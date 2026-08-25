"""
notification_curator.py — Stage 3. Say what was decided.

THE BOUNDARY THIS MODULE DEFENDS: the outcome arrives already decided. The
curator receives a finished Decision and writes prose for it. It cannot choose
an outcome, cannot invent a saving, and cannot promise a deadline.

That is not a limitation, it is the design. A model that could decide *and*
describe would make the decision unauditable, and the whole margin argument
rests on the decision being reproducible.

Copy is Indonesian, formal-but-warm, addressing the traveler as Anda. House
rules, enforced after generation rather than merely requested:

  no emoji            checked and stripped
  no invented numbers only figures passed in are allowed through
  no fake deadline    a deadline line is only ever appended by the template
                      layer, and only when a carrier genuinely guaranteed the
                      fare -- the model is never given the expiry to play with

On any failure the deterministic templates in notifications.py take over.
"""
from __future__ import annotations

import logging
from typing import Optional

from . import llm, notifications
from .formatting import idr, plain_pct
from .schemas import Decision, HoldStatus, NotificationDraft, Outcome

logger = logging.getLogger(__name__)

SYSTEM = """You are the Notification Curator stage of Windfall, an
abandoned-cart recovery pipeline for an Indonesian online travel agency.

You are given a traveler, their abandoned cart, and a decision that has ALREADY
BEEN MADE by an earlier stage. Write the message that communicates that
decision.

Language: Indonesian. Formal but warm. Address the traveler as "Anda".

Rules you must follow:
- You do not decide anything. Describe the decision you were given.
- Use only the figures supplied. Never compute, round, or invent a number.
- No emoji. No exclamation marks. No manufactured urgency.
- Never mention a deadline, a countdown, or an expiring offer. If one applies
  it is added separately.
- On the "reminder" outcome nothing has changed and there is nothing to claim.
  Do not imply a missed deal, a discount, or a limited window. Say plainly that
  the trip is still saved exactly as they left it.
- On "rebuild" or "lateral" the price is lower because the TRIP CHANGED, not
  because a discount was applied. Never use the word "diskon" for it.
- On "lateral" the star rating did NOT drop. Do not describe it as a downgrade.

Respond with strict JSON:
{"subject": "...", "bodyParagraphs": ["...", "...", "..."], "whatsapp": "...", "ctaLabel": "..."}
"""

_EMOJI_FLOOR = 0x2190


def _clean(text: str) -> str:
    """Strip anything above the symbol floor. Belt and braces on 'no emoji'."""
    return "".join(ch for ch in (text or "") if ord(ch) < _EMOJI_FLOOR).strip()


def curate(cart, traveler_name: str, decision: Decision, hold: HoldStatus,
           tier: str, alternative_label: Optional[str] = None,
           alternative_desc: Optional[str] = None) -> NotificationDraft:
    """Returns a draft. Never raises; falls back to templates."""
    fallback = notifications.draft(
        cart, traveler_name, decision, hold,
        alternative_label=alternative_label, alternative_desc=alternative_desc)

    payload = {
        "traveler": {"name": traveler_name, "tier": tier},
        "cart": {
            "route": "{} -> {}".format(cart.flight.origin, cart.flight.destination),
            "carrier": cart.flight.carrier,
            "city": cart.hotel.city,
            "hotel": cart.hotel.name,
            "hotelStars": cart.hotel.stars,
            "area": cart.hotel.area,
            "originalTotal": idr(cart.total_idr),
        },
        "decision": {
            "outcome": decision.outcome,
            "rationale": decision.rationale,
            "finalTotal": idr(decision.final_total_idr),
            "traveleSaves": idr(decision.saving_idr) if decision.saving_idr else None,
            "savingPercent": (plain_pct(decision.saving_pct)
                              if decision.saving_pct else None),
            "whatChanged": _what_changed(decision),
        },
        "alternative": ({"label": alternative_label, "description": alternative_desc}
                        if decision.outcome == Outcome.ALTERNATIVE else None),
    }

    result = llm.complete_json(SYSTEM, payload, label="notifier")
    if not result:
        return NotificationDraft(
            subject=fallback.subject, body_paragraphs=fallback.body_paragraphs,
            whatsapp=fallback.whatsapp, cta_label=fallback.cta_label,
            channel_note=fallback.channel_note,
            written_by="deterministic ({})".format(llm.why_unavailable()))

    subject = _clean(result.get("subject", ""))
    paragraphs = [_clean(p) for p in (result.get("bodyParagraphs") or []) if _clean(p)]
    whatsapp = _clean(result.get("whatsapp", ""))
    cta = _clean(result.get("ctaLabel", ""))

    if not (subject and len(paragraphs) >= 2 and whatsapp and cta):
        logger.warning("[curator] incomplete draft; using templates")
        return NotificationDraft(
            subject=fallback.subject, body_paragraphs=fallback.body_paragraphs,
            whatsapp=fallback.whatsapp, cta_label=fallback.cta_label,
            channel_note=fallback.channel_note,
            written_by="deterministic (model returned an incomplete draft)")

    # The deadline is appended here, never generated. The model is not given
    # the expiry, so it cannot promise one that a carrier has not guaranteed.
    if hold.may_render_deadline:
        paragraphs.append(
            "Harga penerbangan dijamin maskapai sampai {}. Tarif hotel masih "
            "dihitung ulang saat pembayaran.".format(hold.expires_at))

    return NotificationDraft(
        subject=subject, body_paragraphs=tuple(paragraphs), whatsapp=whatsapp,
        cta_label=cta, channel_note=fallback.channel_note, written_by="gemini")


def _what_changed(decision: Decision) -> Optional[str]:
    for attempt in decision.attempts:
        if attempt.cleared and attempt.hotel is not None:
            return "{} ({} bintang)".format(attempt.hotel.name, attempt.hotel.stars)
    return None
