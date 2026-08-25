"""
pipeline.py — Classifier, Searcher, Notification Curator, in that order.

Everything happens inside one synchronous call. No thread, no queue, no
scheduler: the whole trace is assembled and returned in the response body of
the request that triggered it.

Stage durations are measured, not invented. In live mode they are wall-clock
for that request; in fixture mode they are the durations captured from a
recorded live run and replayed verbatim. Either way the console is showing a
number that actually happened, which is the only version of "real durations"
worth claiming.
"""
from __future__ import annotations

import time
from dataclasses import replace
from typing import Callable, List, Optional, Tuple

from . import (classifier_agent, gate, hold_manager, ladder, llm, mcp_tools,
               notification_curator, outcomes, providers, repository,
               searcher_agent, tiers)
import logging

from .schemas import (
    Classification, HoldState, HoldStatus, RecoveryResult, StageTiming,
)


class _Clock:
    """Measures each stage, or yields a captured duration in fixture mode."""

    def __init__(self, captured: Optional[dict] = None):
        self.captured = captured or {}
        self.timings: List[StageTiming] = []

    def stage(self, name: str, fn: Callable):
        start = time.perf_counter()
        result = fn()
        measured = int((time.perf_counter() - start) * 1000)
        self.timings.append(StageTiming(name, self.captured.get(name, measured)))
        return result


logger = logging.getLogger(__name__)


def _live_flight_price(row: dict) -> int:
    """
    Current flight price, for composing live rung candidates.

    NOT p_0. The original cart price is the abandonment price in the seed; this
    is today's quote for the same flight, which the ladder adds to each
    candidate hotel. Confirming a flight is still priceable also fails fast
    when inventory is down, before three rungs are attempted.
    """
    f, h = row["cart"]["flight"], row["cart"]["hotel"]

    flights = mcp_tools.call_tool(
        "search_flights", origin=f["origin"], destination=f["destination"],
        depart_date=f["departDate"], cabin=f["cabin"])
    if not flights:
        raise providers.CarrierInventoryUnavailable("no flight offers returned")
    flight_idr = min(int(o.get("priceIdr", 0) or 0) for o in flights)

    if flight_idr <= 0:
        raise providers.CarrierInventoryUnavailable("inventory returned no usable price")
    return flight_idr


def run(traveler_id: str) -> RecoveryResult:
    # Refuse an unconfigured live run before any stage produces prose. A live
    # run with no GEMINI_API_KEY would otherwise return a complete-looking
    # trace whose reasoning is deterministic templates -- indistinguishable
    # from model output at a glance, which is exactly the claim this project
    # must not make by accident.
    llm.require_configured()

    history, row = repository.get(traveler_id)
    # Narrated at INFO so a demo can put the terminal on screen beside the
    # console. Console output only -- nothing is persisted.
    logger.info("[pipeline] === %s (%s) ===", history.name, traveler_id)
    logger.info("[pipeline] prices=%s inference=%s",
                "replayed capture" if providers.use_fixtures() else "live providers",
                "gemini" if llm.available() else llm.why_unavailable())
    cart_id = row["cart"]["cartId"]
    fixture_mode = providers.use_fixtures()
    captured = providers.fixtures().get("timings_ms", {}).get(cart_id) if fixture_mode else None
    clock = _Clock(captured)

    # ── Prices ──────────────────────────────────────────────────────────────
    # Fixture mode replays captured totals; live mode re-queries through the
    # MCP tools. The two must genuinely differ: an earlier revision always used
    # the fixture provider and only changed the `source` label, which meant
    # WINDFALL_FIXTURES=0 dropped the "replaying capture" badge while still
    # replaying the capture. That is precisely the "cached for reliability
    # quietly becoming faked" failure the flag exists to prevent.
    error: Optional[str] = None
    provider = None
    alternative_total = None

    if fixture_mode:
        try:
            provider = providers.FixtureProvider(cart_id)
            alternative_total = provider.alternative()
        except providers.CarrierInventoryUnavailable as exc:
            error = str(exc)
    else:
        try:
            provider = providers.LiveProvider(
                cart_id, _live_flight_price(row),
                lambda **kw: mcp_tools.call_tool("search_hotels", **kw))
            # No live source proposes an alternative destination; that rung is
            # fixture-only until the roadmap work in section 5.3 lands.
            alternative_total = None
        except providers.CarrierInventoryUnavailable as exc:
            error = str(exc)
        except Exception as exc:
            # A live search that cannot price the cart is an upstream failure,
            # reported as one rather than silently falling back to fixtures --
            # a fallback there would make live mode indistinguishable from
            # replay, which is the whole thing being guarded against.
            error = "carrier_inventory_unavailable: {}".format(exc)

    # p_0 is the abandonment price and does not depend on today's inventory,
    # so the cart is built the same way whether or not the search succeeded.
    cart = repository.build_cart(row)
    original_total = cart.total_idr

    # ── Stage 1: Classifier ─────────────────────────────────────────────────
    def _classify():
        tier, source = tiers.assign_tier(history, cart, repository.reference_spend())
        g = gate.evaluate(history, original_total) if original_total else None
        return tier, source, g

    tier, tier_source, gate_result = clock.stage("classifier", _classify)

    if error is not None:
        logger.info("[pipeline] stage 1/3 Classifier (deterministic tier only)")
        logger.info("[pipeline] stages 2/3 and 3/3 SKIPPED: %s", error)
        logger.info("[pipeline] OUTCOME = error | nothing drafted, nothing sent")
        # The classifier completed; the searcher cannot run. Reported plainly
        # rather than dressed up as a decision the pipeline did not make.
        clock.timings.append(StageTiming("searcher", (captured or {}).get("searcher", 0)))
        classification = Classification(
            tier=tier, tier_prior=tier, threshold=tiers.threshold_for(tier),
            reasoning=tuple(classifier_agent._fallback_reasoning(
                history, cart, tier_source, gate_result)),
            is_cold_start=history.is_cold_start, tier_source=tier_source,
        )
        from .schemas import Decision, GateResult, Outcome
        unevaluated = gate_result or GateResult(
            opened=False, campaign_share=history.campaign_share,
            budget_gap=0.0, price_sensitive=None, over_budget=False,
            reason=("Gate tidak dievaluasi: total cart tidak dapat dihitung "
                    "karena inventaris maskapai tidak tersedia."),
        )
        return RecoveryResult(
            cart_id=cart_id, traveler_id=traveler_id, traveler_name=history.name,
            classification=classification, gate=unevaluated,
            decision=Decision(outcome=Outcome.ERROR, cleared_rung=None,
                              rationale=("Inventaris maskapai sedang tidak "
                                         "tersedia, sehingga rebuild tidak "
                                         "dapat dijalankan.")),
            hold=HoldStatus(state=HoldState.NOT_ELIGIBLE,
                            carrier=cart.flight.carrier),
            notification=None, timings=tuple(clock.timings),
            original_total_idr=original_total,
            source="fixture" if fixture_mode else "live",
        )

    # The Classifier may move the tier one step off the percentile prior with a
    # stated reason; the prior is recorded either way so the move is arguable.
    logger.info("[pipeline] stage 1/3 Classifier")
    classification = classifier_agent.classify(
        history, cart, tier_prior=tier, tier_source=tier_source,
        gate_result=gate_result, reference_spend=repository.reference_spend())
    threshold = classification.threshold

    # ── Stage 2: Searcher ───────────────────────────────────────────────────
    logger.info("[pipeline] stage 2/3 Searcher")

    def _search():
        if not gate_result.opened:
            return ()
        return ladder.run(cart, threshold, provider)

    attempts = clock.stage("searcher", _search)

    # Comparability is the model's job here; the threshold arithmetic already
    # happened in ladder.py and is not up for revision.
    notes = searcher_agent.assess(cart, classification.tier, threshold, attempts)
    if notes:
        attempts = tuple(
            replace(a, note=notes[a.index]["note"]) if a.index in notes else a
            for a in attempts)

    decision = outcomes.decide(gate_result, original_total, attempts, alternative_total)
    logger.info("[pipeline] gate %s (share=%s gap=%s) -> tier %s, threshold %s",
                "OPENED" if gate_result and gate_result.opened else "CLOSED",
                getattr(gate_result, "campaign_share", None),
                getattr(gate_result, "budget_gap", None),
                classification.tier, threshold)
    for a in decision.attempts:
        logger.info("[pipeline]   rung %s %-42s delta=%s %s",
                    a.index, a.label, a.delta, "CLEARED" if a.cleared else "below threshold")
    logger.info("[pipeline] OUTCOME = %s | saving %s | margin conceded %s",
                decision.outcome, decision.saving_idr, decision.margin_conceded_idr)

    # Hold eligibility, read-only. There is no create_hold anywhere in this
    # package: placing a hold is a real write against airline inventory.
    hold = hold_manager.evaluate(cart_id, cart.flight.carrier)

    # ── Stage 3: Notification Curator ───────────────────────────────────────
    alt = (providers.fixtures().get("alternatives") or {}).get(cart_id) or {}

    logger.info("[pipeline] stage 3/3 Notification Curator")

    def _draft():
        return notification_curator.curate(
            cart, history.name, decision, hold, classification.tier,
            alternative_label=alt.get("label"),
            alternative_desc=alt.get("description"))

    notification = clock.stage("notifier", _draft)

    return RecoveryResult(
        cart_id=cart_id, traveler_id=traveler_id, traveler_name=history.name,
        classification=classification, gate=gate_result, decision=decision,
        hold=hold, notification=notification, timings=tuple(clock.timings),
        original_total_idr=original_total,
        source="fixture" if fixture_mode else "live",
    )
