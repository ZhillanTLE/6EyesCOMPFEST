"""
schemas.py — Contracts for every boundary in the recovery pipeline.

Plain stdlib dataclasses: the repo has no pydantic and this needs none. Each
type is the agreed shape at one seam, so the frontend, the agents and the
deterministic core can all be built against it independently.

The load-bearing rule this file encodes: reasoning is the agents' job, and
arithmetic is not. Every monetary figure and every threshold comparison is
computed here or in ladder.py and handed to the model already decided. An
agent may explain a Decision; it may never produce one.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional, Sequence


# ── Inputs ───────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TravelerHistory:
    """What read_traveler_history returns. Seed-backed now, live later."""
    traveler_id: str
    name: str
    booking_count: int
    # Mean total spend per trip, in IDR. Doubles as the budget-gap baseline
    # s-bar_i (paper §3.2.1), which is why tier and gap are not independent.
    usual_spend: int
    # Share of historical spend on discounted product, 0.0-1.0.
    # None when booking_count <= COLD_START_MAX_BOOKINGS: unmeasurable, and a
    # fabricated value here would silently fake the price-sensitivity signal.
    campaign_share: Optional[float]
    avg_hotel_stars: Optional[float] = None
    premium_cabin_share: Optional[float] = None

    @property
    def is_cold_start(self) -> bool:
        from . import config
        return self.booking_count <= config.COLD_START_MAX_BOOKINGS


@dataclass(frozen=True)
class HotelSpec:
    name: str
    stars: int
    city: str
    area: str
    check_in: str          # ISO date
    check_out: str         # ISO date
    price_idr: int = 0


@dataclass(frozen=True)
class FlightSpec:
    """Pinned across every ladder rung so a Hold Order stays valid."""
    carrier: str
    origin: str            # IATA
    destination: str       # IATA
    depart_date: str       # ISO date
    return_date: Optional[str]
    cabin: str
    passengers: int
    price_idr: int = 0
    duffel_offer_id: Optional[str] = None


@dataclass(frozen=True)
class AbandonedCart:
    cart_id: str
    traveler_id: str
    flight: FlightSpec
    hotel: HotelSpec
    abandoned_hours_ago: int

    @property
    def total_idr(self) -> int:
        return self.flight.price_idr + self.hotel.price_idr


# ── Classification ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Classification:
    """
    Output of the Classifier Agent.

    Two tiers are recorded, not one. `tier_prior` is the deterministic
    percentile result; `tier` is what the agent concluded. When they differ the
    agent must say why in `override_reason`. Without this split, "penalaran,
    bukan pencocokan tabel" (paper §3.2.4) is an unfalsifiable claim.
    """
    tier: str
    tier_prior: str
    threshold: float                     # tau(tier)
    reasoning: Sequence[str] = field(default_factory=tuple)
    override_reason: Optional[str] = None
    is_cold_start: bool = False
    tier_source: str = "history"         # "history" | "cart_proxy"


# ── Ladder ───────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class LadderAttempt:
    """
    One rung, priced. `delta` is the relative saving against the original cart:
    (p0 - pk) / p0. Positive means cheaper.

    `cleared` is delta >= tau, computed here and never inferred by a model.
    An attempt that returns no candidate at all is `available=False`, which is
    a different fact from an attempt that priced but missed the threshold --
    the ledger must be able to show both.
    """
    index: int
    rung: str
    label: str
    available: bool
    total_idr: Optional[int]
    delta: Optional[float]
    cleared: bool
    hotel: Optional[HotelSpec] = None
    note: Optional[str] = None


# ── Decision ─────────────────────────────────────────────────────────────────

class Outcome:
    """
    The four terminal outcomes, plus the error state the live-API reality
    forces on us.

    REBUILD and LATERAL are both "a rung cleared" -- they are separated because
    they read completely differently to a traveler. A lateral swap keeps the
    same star rating and is not a downgrade; a tier-down is. Collapsing them
    would hide the one the product is least embarrassed about.

    REMINDER is a decision, not an absence. It renders at equal weight.
    """
    REBUILD = "rebuild"
    LATERAL = "lateral"
    REMINDER = "reminder"
    ALTERNATIVE = "alternative"
    ERROR = "error"

    ALL = (REBUILD, LATERAL, REMINDER, ALTERNATIVE, ERROR)
    # Outcomes that put a changed cart in front of the traveler.
    INTERVENING = (REBUILD, LATERAL, ALTERNATIVE)


@dataclass(frozen=True)
class GateResult:
    """
    The two-axis test from paper §4.1:
        rebuild ladder  iff  c_i >= c*  AND  g_i > 0
    Campaign share alone never opens the gate; neither does a budget gap alone.
    """
    opened: bool
    campaign_share: Optional[float]
    budget_gap: float                    # g_i = (p0 - s-bar_i) / s-bar_i
    price_sensitive: Optional[bool]      # None when campaign_share is unknown
    over_budget: bool
    reason: str
    cold_start_exception: bool = False


@dataclass(frozen=True)
class Decision:
    outcome: str
    cleared_rung: Optional[str]          # which LADDER rung cleared, if any
    attempts: Sequence[LadderAttempt] = field(default_factory=tuple)
    final_total_idr: Optional[int] = None
    saving_idr: int = 0                  # what the TRAVELER saves
    saving_pct: Optional[float] = None
    margin_conceded_idr: int = 0         # what the PARTNER gives up. Always 0.
    rationale: str = ""


# ── Hold Order ───────────────────────────────────────────────────────────────

class HoldState:
    ELIGIBLE = "eligible"                # carrier guarantees the fare
    NOT_ELIGIBLE = "not_eligible"        # no deadline may be rendered at all
    SIMULATED = "simulated"              # pre-auth fallback, labelled as such


@dataclass(frozen=True)
class HoldStatus:
    """
    Covers the FLIGHT only. The hotel re-prices at conversion, and the UI must
    say so rather than implying the whole cart is frozen.
    """
    state: str
    expires_at: Optional[str] = None     # ISO 8601, from payment_required_by
    carrier: Optional[str] = None
    note: Optional[str] = None

    @property
    def may_render_deadline(self) -> bool:
        """A countdown appears only when a carrier genuinely guarantees it."""
        return self.state == HoldState.ELIGIBLE and bool(self.expires_at)


# ── Output ───────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class StageTiming:
    """Measured wall-clock, never synthesised. The client replays these."""
    stage: str
    duration_ms: int


@dataclass(frozen=True)
class NotificationDraft:
    subject: str
    body_paragraphs: Sequence[str]
    whatsapp: str
    cta_label: str
    channel_note: Optional[str] = None


@dataclass(frozen=True)
class RecoveryResult:
    cart_id: str
    traveler_name: str
    classification: Classification
    gate: GateResult
    decision: Decision
    hold: HoldStatus
    notification: Optional[NotificationDraft]
    timings: Sequence[StageTiming]
    original_total_idr: int
    source: str = "live"                 # "live" | "fixture"

    def to_dict(self) -> dict:
        """camelCase on the wire, per the data contract. Python stays snake."""
        from .serialize import camelize
        return camelize(asdict(self))
