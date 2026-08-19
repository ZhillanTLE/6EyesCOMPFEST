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
from typing import Callable, List, Optional, Tuple

from . import config, gate, ladder, notifications, outcomes, providers, repository, tiers
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


def _classifier_reasoning(history, cart, tier, tier_source, gate_result) -> List[str]:
    """
    Evidence lines that cite the actual numbers behind the tier.

    Deterministic by design. classifier_agent.py substitutes Gemini for the
    live path against this same shape, and falls back here when no key is
    configured -- the demo must not depend on a network call to be legible.
    """
    from .formatting import idr, plain_pct

    lines = ["Membaca {} pemesanan historis via read_traveler_history".format(
        history.booking_count)]
    if tier_source == "cart_proxy":
        lines.append(
            "Tanpa riwayat memadai; tingkatan diturunkan dari isi cart "
            "(kelas {}, hotel {} bintang)".format(cart.flight.cabin, cart.hotel.stars))
    else:
        lines.append("Rata-rata pengeluaran {} per perjalanan".format(
            idr(history.usual_spend)))
    if history.campaign_share is None:
        lines.append("Campaign share tidak terukur - tidak ada riwayat diskon")
    else:
        lines.append("Campaign share {} terhadap ambang {}".format(
            plain_pct(history.campaign_share), plain_pct(config.C_STAR)))
    if gate_result is None:
        lines.append("Total cart tidak dapat dihitung - inventaris tidak tersedia")
    else:
        lines.append("Cart {} terhadap pengeluaran biasa".format(
            plain_pct(gate_result.budget_gap)))
    return lines


def run(traveler_id: str) -> RecoveryResult:
    history, row = repository.get(traveler_id)
    cart_id = row["cart"]["cart_id"]
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
            reasoning=tuple(_classifier_reasoning(
                history, cart, tier, tier_source, gate_result)),
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
            cart_id=cart_id, traveler_name=history.name,
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

    threshold = tiers.threshold_for(tier)
    classification = Classification(
        tier=tier, tier_prior=tier, threshold=threshold,
        reasoning=tuple(_classifier_reasoning(
            history, cart, tier, tier_source, gate_result)),
        is_cold_start=history.is_cold_start, tier_source=tier_source,
    )

    # ── Stage 2: Searcher ───────────────────────────────────────────────────
    def _search():
        if not gate_result.opened:
            return ()
        return ladder.run(cart, threshold, provider)

    attempts = clock.stage("searcher", _search)
    decision = outcomes.decide(gate_result, original_total, attempts, alternative_total)
    hold = providers.hold_status(cart_id, cart.flight.carrier)

    # ── Stage 3: Notification Curator ───────────────────────────────────────
    alt = (providers.fixtures().get("alternatives") or {}).get(cart_id) or {}

    def _draft():
        return notifications.draft(
            cart, history.name, decision, hold,
            alternative_label=alt.get("label"),
            alternative_desc=alt.get("description"))

    notification = clock.stage("notifier", _draft)

    return RecoveryResult(
        cart_id=cart_id, traveler_name=history.name,
        classification=classification, gate=gate_result, decision=decision,
        hold=hold, notification=notification, timings=tuple(clock.timings),
        original_total_idr=original_total,
        source="fixture" if fixture_mode else "live",
    )
