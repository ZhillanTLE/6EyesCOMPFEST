"""
ladder.py — The rebuild ladder (paper section 4.1, Tabel 1.6 as amended).

    k* = min { k : delta_k >= tau(T_i) }

Rungs run smallest-change-first and evaluation stops at the first one that
clears the tier threshold, so the recovered cart stays as close to what the
traveler actually chose as the threshold allows.

Two properties this module exists to guarantee:

  1. All arithmetic is here. An agent judges whether a rung is worth showing
     in prose; it never computes delta and never decides `cleared`. Paper
     section 4 is explicit that transactional figures must be reproducible.

  2. "Priced but missed" and "nothing found" stay distinguishable. A lateral
     swap that exists but only saves 2% is a real finding -- it is the
     evidence that restraint was earned rather than assumed -- and the ledger
     has to be able to render it as such.

The flight is pinned across every rung. A Duffel Hold Order is held against a
specific flight offer, so swapping the flight would void the guarantee the
freeze exists to provide; hotel substitution is also margin-neutral inventory
composition, which keeps the zero-margin-conceded claim intact.
"""
from __future__ import annotations

from typing import Callable, List, Optional, Sequence

from . import config
from .schemas import AbandonedCart, HotelSpec, LadderAttempt

# A provider prices one rung against a cart and returns either a candidate or
# None when the inventory has nothing to offer on that rung.
#   (rung, cart) -> Optional[RungCandidate]
RungProvider = Callable[[str, AbandonedCart], Optional["RungCandidate"]]


class RungCandidate:
    """What a provider hands back: a priced alternative composition."""

    __slots__ = ("total_idr", "hotel", "note")

    def __init__(self, total_idr: int, hotel: Optional[HotelSpec] = None,
                 note: Optional[str] = None):
        self.total_idr = int(total_idr)
        self.hotel = hotel
        self.note = note


RUNG_LABELS = {
    config.RUNG_REPRICE: "Same cart, re-priced",
    config.RUNG_LATERAL: "Same-star hotel swap, same area and dates",
    config.RUNG_TIER_DOWN: "Hotel down one star, same area and dates",
}


def relative_saving(original_idr: int, candidate_idr: int) -> float:
    """delta_k = (p_0 - p_k) / p_0. Positive means cheaper than the original."""
    if original_idr <= 0:
        raise ValueError("original cart total must be positive")
    return (original_idr - candidate_idr) / original_idr


def run(
    cart: AbandonedCart,
    tau: float,
    provider: RungProvider,
    rungs: Sequence[str] = config.LADDER,
) -> List[LadderAttempt]:
    """
    Walk the ladder, stopping after the first rung that clears `tau`.

    Returns every rung actually attempted, in order, including the failures
    before the winner. Rungs after the winner are never priced -- that is the
    point of stopping -- so they simply do not appear.
    """
    original = cart.total_idr
    attempts: List[LadderAttempt] = []

    for i, rung in enumerate(rungs, start=1):
        candidate = provider(rung, cart)

        if candidate is None:
            attempts.append(LadderAttempt(
                index=i, rung=rung, label=RUNG_LABELS.get(rung, rung),
                available=False, total_idr=None, delta=None, cleared=False,
                note="No comparable option returned for this rung.",
            ))
            continue

        delta = relative_saving(original, candidate.total_idr)
        cleared = delta >= tau
        attempts.append(LadderAttempt(
            index=i, rung=rung, label=RUNG_LABELS.get(rung, rung),
            available=True, total_idr=candidate.total_idr, delta=delta,
            cleared=cleared, hotel=candidate.hotel, note=candidate.note,
        ))
        if cleared:
            break

    return attempts


def winner(attempts: Sequence[LadderAttempt]) -> Optional[LadderAttempt]:
    """The cleared rung, if any. At most one by construction."""
    for a in attempts:
        if a.cleared:
            return a
    return None
