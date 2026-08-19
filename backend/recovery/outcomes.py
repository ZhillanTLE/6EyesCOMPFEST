"""
outcomes.py — Assembles a Decision from the gate result and the ladder.

This is the only place an outcome is chosen. Nothing upstream pre-assigns one
and no agent infers one: the Notification Curator receives the finished
Decision and writes prose for it.

    gate closed                -> REMINDER
    gate open, a rung cleared  -> LATERAL (same-star swap) or REBUILD
    gate open, nothing cleared -> ALTERNATIVE if one exists, else REMINDER

That last fallback is deliberate. "We looked, found options, and none of them
were worth putting in front of you" has to remain a reachable end state, or
restraint stops being an outcome the system can actually produce and becomes
just a label for the cases it happened not to solve.
"""
from __future__ import annotations

from typing import Optional, Sequence

from . import config
from .formatting import plain_pct
from .ladder import winner
from .schemas import Decision, GateResult, LadderAttempt, Outcome

# Which rung maps to which traveler-facing outcome. A lateral swap keeps the
# same star rating and is not a downgrade; collapsing it into REBUILD would
# hide the one result the product is least apologetic about.
_RUNG_OUTCOME = {
    config.RUNG_REPRICE: Outcome.REBUILD,
    config.RUNG_LATERAL: Outcome.LATERAL,
    config.RUNG_TIER_DOWN: Outcome.REBUILD,
}


def decide(
    gate: GateResult,
    original_total_idr: int,
    attempts: Sequence[LadderAttempt] = (),
    alternative_total_idr: Optional[int] = None,
) -> Decision:
    if not gate.opened:
        return Decision(
            outcome=Outcome.REMINDER,
            cleared_rung=None,
            attempts=tuple(attempts),
            final_total_idr=original_total_idr,
            saving_idr=0,
            saving_pct=None,
            margin_conceded_idr=0,
            rationale=gate.reason,
        )

    won = winner(attempts)
    if won is not None and won.total_idr is not None:
        saving = original_total_idr - won.total_idr
        rung_label = won.label.lower()
        if won.rung == config.RUNG_REPRICE:
            rationale = (
                "The same cart re-priced {} below where the traveler left "
                "it, which clears the tier threshold on its own. Nothing about "
                "the trip changed."
            ).format(plain_pct(won.delta or 0.0))
        else:
            rationale = (
                "Attempt {} ({}) cleared the tier threshold at {}. The "
                "flight, dates and area are unchanged."
            ).format(won.index, rung_label, plain_pct(won.delta or 0.0))
        return Decision(
            outcome=_RUNG_OUTCOME.get(won.rung, Outcome.REBUILD),
            cleared_rung=won.rung,
            attempts=tuple(attempts),
            final_total_idr=won.total_idr,
            saving_idr=saving,
            saving_pct=won.delta,
            margin_conceded_idr=0,
            rationale=rationale,
        )

    # Nothing cleared.
    priced = [a for a in attempts if a.available and a.delta is not None]
    best = max((a.delta for a in priced), default=None)

    if alternative_total_idr is not None:
        saving = original_total_idr - alternative_total_idr
        if best is None:
            detail = "No rung returned a comparable option."
        else:
            detail = "The best rung saved only {}.".format(plain_pct(best))
        return Decision(
            outcome=Outcome.ALTERNATIVE,
            cleared_rung=None,
            attempts=tuple(attempts),
            final_total_idr=alternative_total_idr,
            saving_idr=saving,
            saving_pct=(saving / original_total_idr) if original_total_idr else None,
            margin_conceded_idr=0,
            rationale=(
                "No rebuild of the original trip cleared the tier threshold. "
                + detail
                + " Rather than discount below margin, a different trip within "
                "the same budget is proposed."
            ),
        )

    if best is None:
        detail = "No rung returned a comparable option, and no alternative trip fits."
    else:
        detail = (
            "The best rung saved only {}, short of the threshold, and no "
            "alternative trip fits."
        ).format(plain_pct(best))
    return Decision(
        outcome=Outcome.REMINDER,
        cleared_rung=None,
        attempts=tuple(attempts),
        final_total_idr=original_total_idr,
        saving_idr=0,
        saving_pct=None,
        margin_conceded_idr=0,
        rationale=detail + " The cart is left exactly as it was.",
    )
