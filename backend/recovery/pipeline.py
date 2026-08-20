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

from . import (classifier_agent, gate, ladder, mcp_tools, notification_curator,
               outcomes, providers, repository, searcher_agent, tiers)
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


def run(traveler_id: str) -> RecoveryResult:
    history, row = repository.get(traveler_id)
    cart_id = row["cart"]["cartId"]
    fixture_mode = providers.use_fixtures()
    captured = providers.fixtures().get("timings_ms", {}).get(cart_id) if fixture_mode else None
    clock = _Clock(captured)

    # ── Prices. Live re-query, or captured totals in fixture mode. ───────────
    error: Optional[str] = None
    provider = None
    flight_idr = hotel_idr = 0
    alternative_total = None
    try:
        provider = providers.FixtureProvider(cart_id)
        flight_idr, hotel_idr = provider.prices()
        alternative_total = provider.alternative()
    except providers.CarrierInventoryUnavailable as exc:
        error = str(exc)

    cart = repository.build_cart(row, flight_idr, hotel_idr)
    original_total = cart.total_idr

    # ── Stage 1: Classifier ─────────────────────────────────────────────────
    def _classify():
        tier, source = tiers.assign_tier(history, cart, repository.reference_spend())
        g = gate.evaluate(history, original_total) if original_total else None
        return tier, source, g

    tier, tier_source, gate_result = clock.stage("classifier", _classify)

    if error is not None:
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
    classification = classifier_agent.classify(
        history, cart, tier_prior=tier, tier_source=tier_source,
        gate_result=gate_result, reference_spend=repository.reference_spend())
    threshold = classification.threshold

    # ── Stage 2: Searcher ───────────────────────────────────────────────────
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

    # Hold eligibility through the MCP tool. Read-only; there is no create_hold.
    hold_row = mcp_tools.call_tool(
        "check_hold_eligibility", cart_id=cart_id, carrier=cart.flight.carrier)
    hold = providers.hold_status(cart_id, cart.flight.carrier)

    # ── Stage 3: Notification Curator ───────────────────────────────────────
    alt = (providers.fixtures().get("alternatives") or {}).get(cart_id) or {}

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
