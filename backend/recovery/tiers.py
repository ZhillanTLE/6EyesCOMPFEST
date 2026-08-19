"""
tiers.py — Deterministic tier assignment (paper §3.2.4, §3.2.5).

Produces the *prior* only. The Classifier Agent may move a traveler one step
off this prior with a stated reason; that happens in classifier_agent.py, not
here. Keeping the prior deterministic is what makes the agent's override
visible and arguable instead of invisible.
"""
from __future__ import annotations

from typing import Sequence

from . import config
from .schemas import AbandonedCart, TravelerHistory


def percentile_rank(value: float, distribution: Sequence[float]) -> float:
    """
    q_i = F_M(m_i): the share of the reference distribution at or below `value`.

    Empirical CDF, no interpolation -- with a seed this small, interpolating
    would imply a precision the sample does not have.
    """
    if not distribution:
        raise ValueError("percentile_rank needs a non-empty reference distribution")
    at_or_below = sum(1 for m in distribution if m <= value)
    return at_or_below / len(distribution)


def tier_from_percentile(q: float) -> str:
    low, high = config.TIER_PERCENTILE_CUTS
    if q <= low:
        return config.TIER_VALUE
    if q <= high:
        return config.TIER_COMFORT
    return config.TIER_PREMIUM


def tier_from_cart_proxy(cart: AbandonedCart) -> str:
    """
    Cold-start path (paper §3.2.5). With no history there is no monetary
    percentile, so the cart's own composition stands in: cabin class and hotel
    star rating are the two quality signals available at abandonment.

    Deliberately coarse. This is a proxy standing in for a missing measurement,
    and dressing it up with more rules would not make it better informed.
    """
    cabin = (cart.flight.cabin or "").strip().lower()
    stars = cart.hotel.stars or 0

    if cabin in ("business", "first") or stars >= 5:
        return config.TIER_PREMIUM
    if cabin == "premium_economy" or stars == 4:
        return config.TIER_COMFORT
    return config.TIER_VALUE


def assign_tier(
    history: TravelerHistory,
    cart: AbandonedCart,
    reference_spend: Sequence[float],
):
    """
    Returns (tier, source) where source is "history" or "cart_proxy".

    `reference_spend` is the seed's usual_spend distribution. Post-penyisihan
    this becomes the live population, which is exactly why the paper specifies
    percentiles rather than nominal rupiah cutoffs -- the rule survives a
    change of market or currency.
    """
    if history.is_cold_start:
        return tier_from_cart_proxy(cart), "cart_proxy"
    q = percentile_rank(history.usual_spend, reference_spend)
    return tier_from_percentile(q), "history"


def threshold_for(tier: str) -> float:
    """tau(T_i)."""
    if tier not in config.TAU:
        raise ValueError("unknown tier " + repr(tier))
    return config.TAU[tier]
