"""
hold_manager.py — Can this fare be held, and until when?

Paper section 5.2.2 names this module; section 2.1 stakes a promise on it that
the rest of the product has to keep: "tenggat waktu yang ditampilkan ke
pengguna selalu nyata". A deadline on screen must be one an airline actually
gave.

THREE STATES, AND THE MIDDLE ONE MATTERS MOST.

  eligible      The carrier guarantees the fare. `expires_at` comes from
                Duffel's `payment_required_by` and nothing else. This is the
                only state that may render a countdown.

  not_eligible  The carrier requires instant payment. NO deadline is shown at
                all -- not a shorter one, not a softened one, not "book soon".
                An absent guarantee must read as absence.

  simulated     A pre-authorization fallback, explicitly labelled as simulated
                wherever it appears. The paper commits to labelling this and
                the label is the whole point: an unlabelled simulation of a
                real guarantee is just a lie with extra steps.

SCOPE IS THE FLIGHT ONLY. Duffel holds a flight offer; hotels have no
equivalent primitive and re-price at conversion. Every caller gets `scope`
back so the UI can say so rather than implying the whole cart is frozen.

There is no `create_hold` here and there must never be one. Placing a hold is
a real write against airline inventory.
"""
from __future__ import annotations

import logging
from typing import Dict, Optional

from . import providers
from .schemas import HoldState, HoldStatus

logger = logging.getLogger(__name__)

SCOPE = "flight_only"

NOTES = {
    HoldState.ELIGIBLE: ("Harga penerbangan dijamin maskapai. "
                         "Tarif hotel tetap dihitung ulang saat pembayaran."),
    HoldState.NOT_ELIGIBLE: ("Maskapai tidak menjamin harga ini. "
                             "Tidak ada tenggat waktu yang ditampilkan."),
    HoldState.SIMULATED: ("Simulasi pre-authorization - bukan jaminan maskapai."),
}


def from_duffel_offer(offer: Dict, carrier: str) -> HoldStatus:
    """
    Read hold eligibility straight off a Duffel offer.

    The two fields that matter:
      payment_requirements.requires_instant_payment
          False -> the offer can be held and paid for later
      payment_requirements.payment_required_by
          ISO 8601, and the ONLY legitimate source for a countdown

    A missing payment_requirements block is treated as not eligible. Absence of
    evidence is not a guarantee, and defaulting the other way would put an
    invented deadline in front of a traveler.
    """
    requirements = (offer or {}).get("payment_requirements") or {}
    instant = requirements.get("requires_instant_payment")
    expires = requirements.get("payment_required_by")

    if instant is False and expires:
        return HoldStatus(state=HoldState.ELIGIBLE, expires_at=expires,
                          carrier=carrier, note=NOTES[HoldState.ELIGIBLE])

    return HoldStatus(state=HoldState.NOT_ELIGIBLE, expires_at=None,
                      carrier=carrier, note=NOTES[HoldState.NOT_ELIGIBLE])


def evaluate(cart_id: str, carrier: str,
             offer: Optional[Dict] = None) -> HoldStatus:
    """
    Hold status for a cart. Read-only.

    Fixture mode replays a captured eligibility result; live mode reads the
    offer. Either way the invariant holds: an expiry exists only alongside
    `eligible`, which is what `HoldStatus.may_render_deadline` enforces at the
    type level so no UI branch can accidentally show one.
    """
    if providers.use_fixtures():
        return providers.hold_status(cart_id, carrier)

    if offer is None:
        logger.info("[hold] no offer supplied for %s; treating as not eligible", cart_id)
        return HoldStatus(state=HoldState.NOT_ELIGIBLE, carrier=carrier,
                          note=NOTES[HoldState.NOT_ELIGIBLE])

    return from_duffel_offer(offer, carrier)


def as_tool_payload(status: HoldStatus) -> Dict:
    """Shape returned by the check_hold_eligibility MCP tool."""
    return {
        "state": status.state,
        "expiresAt": status.expires_at,
        "carrier": status.carrier,
        "note": status.note,
        "scope": SCOPE,
        "mayRenderDeadline": status.may_render_deadline,
    }
