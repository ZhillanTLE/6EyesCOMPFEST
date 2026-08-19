"""
config.py — Frozen calibration constants for the Windfall recovery pipeline.

Every number that steers a decision lives here and nowhere else. Per the
penyisihan scope rule ("parameter statis saat demonstrasi, tanpa auto-tuning"),
these are constants in code, never learned and never tuned at runtime.

Provenance matters as much as the values. Two kinds of number appear below:

  - CALIBRATED: read off the seed distribution (or chosen against it) and then
    frozen. Not derived from theory. TIER_PERCENTILE_CUTS, C_STAR and TAU are
    all of this kind, and the paper says so in §3.2.4.
  - STRUCTURAL: fixed by the product definition, not by data. LADDER is the
    rung order; changing it changes what "smallest sufficient change" means.
"""

# ── Tier assignment (paper §3.2.4) ───────────────────────────────────────────
# Percentile cutpoints against the seed's monetary distribution.
#   q <= 0.30           -> Value
#   0.30 < q <= 0.80    -> Comfort
#   q > 0.80            -> Premium
# CALIBRATED constants, not derived.
TIER_PERCENTILE_CUTS = (0.30, 0.80)

TIER_VALUE = "Value"
TIER_COMFORT = "Comfort"
TIER_PREMIUM = "Premium"
TIERS = (TIER_VALUE, TIER_COMFORT, TIER_PREMIUM)

# ── Savings thresholds tau(T_i) (paper §2.1, §3.2.4) ─────────────────────────
# Minimum relative saving a rebuild attempt must deliver before it is worth
# putting in front of a traveler of this tier. A higher bar for Premium is
# deliberate: a 5% saving is not a reason to re-open a Premium traveler's cart.
# CALIBRATED constants.
TAU = {
    TIER_VALUE: 0.05,
    TIER_COMFORT: 0.10,
    TIER_PREMIUM: 0.15,
}

# ── Price-sensitivity gate c* (paper §4.1) ───────────────────────────────────
# Share of historical spend made on discounted product, above which a traveler
# is treated as price-sensitive. CALIBRATED: the seed's two clusters sit at
# ~0.09-0.11 and ~0.43-0.50, so 0.25 separates them with margin on both sides.
# Stated plainly for the same reason the percentile cutpoints are: this is a
# chosen constant, not a derived one.
C_STAR = 0.25

# ── Rebuild ladder (paper Tabel 1.6, as amended) ─────────────────────────────
# STRUCTURAL. Ordered smallest-change-first; evaluation stops at the first rung
# that clears tau. The flight is pinned across every rung: a Duffel Hold Order
# is held against a specific flight offer, so swapping the flight would
# invalidate the very price guarantee the freeze exists to provide. Hotel
# substitution is also margin-neutral inventory composition, which keeps the
# §2.3 "zero margin conceded" argument clean.
RUNG_REPRICE = "reprice"        # nothing changes; the same cart is re-quoted
RUNG_LATERAL = "lateral"        # same star, same dates, same area, other property
RUNG_TIER_DOWN = "tier_down"    # hotel drops one star; dates and area unchanged

LADDER = (RUNG_REPRICE, RUNG_LATERAL, RUNG_TIER_DOWN)

# Roadmap rungs (paper §5.3) — declared so the gap is explicit, never executed.
LADDER_ROADMAP = ("date_shift", "combination", "same_cabin_flight_swap")

# ── Cold start (paper §3.2.5, as amended) ────────────────────────────────────
# A traveler with at most this many historical bookings has no measurable
# campaign share. campaign_share is then None -- never a fabricated number --
# and the tier is derived from cart signals (cabin class, hotel star) instead.
COLD_START_MAX_BOOKINGS = 1

# Cold-start carts may still walk the ladder: a rebuild concedes no margin, so
# the thing cold start cannot justify is a margin-costing action, and the
# penyisihan build issues none. See gate.py for where this exception is applied.
COLD_START_MAY_REBUILD = True
