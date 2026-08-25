"""
classifier_agent.py — Stage 1. Who is this traveler?

Paper Tabel 1.7: "Menalar tingkatan dari pola histori, bukan mencocokkan
tabel." The agent reasons a tier from booking history rather than looking one
up. Paper section 3.2.4 grants it room to weigh signals a single monetary
percentile cannot -- spend trajectory, campaign share, the cart in front of it.

WHAT THE AGENT MAY AND MAY NOT DO.

  May: write the evidence lines behind the classification.
  May not: change the tier, choose an outcome, compute a saving, or decide
       whether the gate opens. Those are arithmetic and they live in tiers.py,
       gate.py and ladder.py, where they are reproducible and testable.

THE TIER IS NOT THE MODEL'S TO MOVE. An earlier revision let it shift the tier
one step off the percentile prior with a stated reason. In practice it used the
wrong evidence to do so -- justifying a move with the budget gap and the
campaign share, which are the two GATE axes, not measures of how a traveler
habitually spends. That double-counts one signal into two decisions.

It also had teeth: moving Value to Comfort raises the threshold from 5% to 10%,
so a rung that would have cleared no longer does. The outcome could flip on
reasoning that should never have applied. The tier is now the percentile result
and nothing else, so the threshold a cart is judged against is reproducible
from the seed alone.

`tier_prior` and `tier` are still both recorded; they are now always equal.
"""
from __future__ import annotations

import logging
from typing import List, Optional, Tuple

from . import config, llm, tiers
from .formatting import idr, plain_pct
from .schemas import Classification

logger = logging.getLogger(__name__)

SYSTEM = """You are the Classifier stage of Windfall, an abandoned-cart recovery
pipeline for an Indonesian online travel agency.

You are given one traveler's booking history, the cart they abandoned, and the
tier computed from where their average spend falls in the population
distribution.

Your job is to write short evidence lines citing the actual numbers you were
given. You do NOT choose the tier: it is already decided, deterministically,
and is shown to you only as context for your evidence.

Rules you must follow:
- Never propose, change, or argue with the tier. Treat it as settled fact.
- The tier describes how this traveler HABITUALLY spends. It is not about this
  cart. Never justify it using the budget gap or the campaign share -- those
  are separate signals that a later stage weighs on their own.
- Evidence lines are for an analyst, in English, and must cite real figures
  from the input. Never invent a number.
- Line count matters. Two lines when both the price-sensitivity signal and the
  budget-gap signal are doing work. One line when a single signal settles it.
  Do not pad.
- campaignShare may be null. That means it is unmeasurable, not zero. Say so
  plainly; never estimate it.
- You do not choose what happens to the cart. Another stage decides that.

Respond with strict JSON:
{"reasoning": ["...", "..."]}
"""


def _fallback_reasoning(history, cart, tier_source, gate_result) -> List[str]:
    """
    Deterministic evidence lines. Used when inference is unavailable.

    Same shape and the same asymmetry as the model is asked for, so the console
    cannot tell them apart structurally -- only the trace's `reasonedBy` field
    reports which produced them.
    """
    lines: List[str] = []

    if tier_source == "cart_proxy":
        lines.append(
            "No booking history; tier estimated from the cart itself "
            "({} cabin, {}-star stay)".format(cart.flight.cabin, cart.hotel.stars))
        if gate_result is not None:
            lines.append(
                "Campaign share unmeasurable, so the ladder runs on the proxy "
                "tier -- a rebuild concedes no margin")
        return lines

    if gate_result is None:
        lines.append("Read {} historical bookings via read_traveler_history".format(
            history.booking_count))
        lines.append("Cart total unavailable -- carrier inventory did not respond")
        return lines

    share = plain_pct(history.campaign_share)
    gap = plain_pct(gate_result.budget_gap)

    if gate_result.opened:
        lines.append("Campaign share {} -- price-sensitive".format(share))
        lines.append("Cart {} above usual spend".format(gap))
    elif not gate_result.price_sensitive:
        lines.append("Campaign share {} -- historically pays full price".format(share))
    else:
        lines.append("Cart sits within usual spend; price is not the barrier")

    return lines


def _one_step_apart(a: str, b: str) -> bool:
    order = [config.TIER_VALUE, config.TIER_COMFORT, config.TIER_PREMIUM]
    try:
        return abs(order.index(a) - order.index(b)) <= 1
    except ValueError:
        return False


def classify(history, cart, tier_prior: str, tier_source: str,
             gate_result, reference_spend) -> Classification:
    """
    Returns a Classification. Never raises: inference failure falls back to the
    deterministic prior and template reasoning.
    """
    reasoned_by = "gemini"
    tier = tier_prior
    override: Optional[str] = None
    reasoning: List[str] = []

    payload = {
        "traveler": {
            "name": history.name,
            "bookings": history.booking_count,
            "usualSpendIdr": history.usual_spend,
            "campaignShare": history.campaign_share,
            "avgStars": history.avg_hotel_stars,
            "premiumCabinShare": history.premium_cabin_share,
            "isColdStart": history.is_cold_start,
        },
        "abandonedCart": {
            "route": "{} -> {}".format(cart.flight.origin, cart.flight.destination),
            "carrier": cart.flight.carrier,
            "cabin": cart.flight.cabin,
            "hotel": cart.hotel.name,
            "hotelStars": cart.hotel.stars,
            "totalIdr": cart.total_idr,
            "totalFormatted": idr(cart.total_idr),
        },
        "tierPrior": tier_prior,
        "tierPriorSource": tier_source,
        "thresholds": {t: config.TAU[t] for t in config.TIERS},
        "campaignShareBar": config.C_STAR,
        "budgetGap": None if gate_result is None else gate_result.budget_gap,
        "gateOpened": None if gate_result is None else gate_result.opened,
    }

    result = llm.complete_json(SYSTEM, payload, label="classifier")

    if result:
        lines = [str(x).strip() for x in (result.get("reasoning") or []) if str(x).strip()]
        if lines:
            reasoning = lines[:3]
            # The tier is the percentile result, full stop. If a model still
            # volunteers one -- prompts drift, and this one used to ask for it
            # -- the value is discarded rather than applied, and the discard is
            # logged so the refusal is visible instead of silent.
            volunteered = str(result.get("tier", "")).strip()
            if volunteered and volunteered != tier_prior:
                logger.warning(
                    "[classifier] ignored a volunteered tier %s; the percentile "
                    "prior %s stands", volunteered, tier_prior)
        else:
            result = None

    if not result:
        reasoned_by = "deterministic ({})".format(llm.why_unavailable())
        reasoning = _fallback_reasoning(history, cart, tier_source, gate_result)

    return Classification(
        tier=tier,
        tier_prior=tier_prior,
        threshold=tiers.threshold_for(tier),
        reasoning=tuple(reasoning),
        override_reason=override,
        is_cold_start=history.is_cold_start,
        tier_source=tier_source,
        reasoned_by=reasoned_by,
    )
