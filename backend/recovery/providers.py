"""
providers.py — Where rung prices come from.

Two implementations behind one callable shape:

  FixtureProvider  reads captured totals from a local JSON file. Deterministic,
                   no keys, no network. WINDFALL_FIXTURES=1.
  LiveProvider     re-queries hotel inventory per rung through the MCP tool
                   layer. The default.

Both return full-cart totals, and both leave the flight untouched -- the ladder
substitutes hotels only, so a Duffel Hold Order held against the flight offer
survives every rung.
"""
from __future__ import annotations

import json
import os
from typing import Callable, Dict, Optional

from . import config
from .ladder import RungCandidate
from .schemas import AbandonedCart, HoldState, HoldStatus, HotelSpec

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "seed", "prices.fixture.json")

_fixtures: Optional[dict] = None


def fixtures() -> dict:
    global _fixtures
    if _fixtures is None:
        with open(FIXTURE_PATH, encoding="utf-8") as fh:
            _fixtures = json.load(fh)
    return _fixtures


def use_fixtures() -> bool:
    return os.environ.get("WINDFALL_FIXTURES", "").strip() in ("1", "true", "yes")


class CarrierInventoryUnavailable(RuntimeError):
    """Upstream failure. The searcher halts; the pipeline reports it plainly."""


# ── Fixture path ─────────────────────────────────────────────────────────────

class FixtureProvider:
    def __init__(self, cart_id: str):
        self.cart_id = cart_id
        self.data = fixtures()["carts"].get(cart_id, {})
        if self.data.get("error"):
            raise CarrierInventoryUnavailable(self.data["error"])

    def prices(self):
        """Captured component prices. NOT p_0 -- that is the abandonment price
        in the seed. Retained for composing candidate totals."""
        return int(self.data.get("flight_idr", 0)), int(self.data.get("hotel_idr", 0))

    def alternative(self) -> Optional[int]:
        return self.data.get("alternative_total_idr")

    def __call__(self, rung: str, cart: AbandonedCart) -> Optional[RungCandidate]:
        total = (self.data.get("rungs") or {}).get(rung)
        if total is None:
            return None
        return RungCandidate(int(total), hotel=self._hotel_for(rung, cart))

    def _hotel_for(self, rung: str, cart: AbandonedCart) -> Optional[HotelSpec]:
        h = cart.hotel
        if rung == config.RUNG_REPRICE:
            return h
        if rung == config.RUNG_LATERAL:
            # Same star, same area, same dates. Not a downgrade.
            return HotelSpec(_LATERAL_NAMES.get(cart.cart_id, "Comparable property"),
                             h.stars, h.city, h.area, h.check_in, h.check_out)
        if rung == config.RUNG_TIER_DOWN:
            return HotelSpec(_TIER_DOWN_NAMES.get(cart.cart_id, "One star lower"),
                             max(1, h.stars - 1), h.city, h.area, h.check_in, h.check_out)
        return None


_LATERAL_NAMES = {
    "cart-wf-02": "The Okura Tokyo",
    "cart-wf-03": "Marina Bay Sands",
    "cart-wf-04": "Hyatt Place Dubai",
    "cart-wf-05": "Villa Song Saigon",
}
_TIER_DOWN_NAMES = {
    "cart-wf-02": "Hotel Ryumeikan Tokyo",
    "cart-wf-04": "Premier Inn Dubai",
    "cart-wf-05": "Alagon Central",
}


# ── Live path ────────────────────────────────────────────────────────────────

class LiveProvider:
    """
    Re-queries hotel inventory per rung via the MCP tool layer.

    Deliberately thin: it maps a rung to a star-rating constraint and asks for
    inventory, then adds the untouched flight price back on. Choosing which
    candidate is comparable is a filter, not a judgement -- the judgement of
    whether the result is worth showing belongs to the threshold in ladder.py.
    """

    def __init__(self, cart_id: str, flight_idr: int, search_hotels: Callable):
        self.cart_id = cart_id
        self.flight_idr = flight_idr
        self.search_hotels = search_hotels

    def __call__(self, rung: str, cart: AbandonedCart) -> Optional[RungCandidate]:
        h = cart.hotel
        if rung == config.RUNG_REPRICE:
            target_stars, exclude_current = h.stars, False
        elif rung == config.RUNG_LATERAL:
            target_stars, exclude_current = h.stars, True
        elif rung == config.RUNG_TIER_DOWN:
            target_stars, exclude_current = max(1, h.stars - 1), False
        else:
            return None

        candidates = self.search_hotels(
            city=h.city, area=h.area, stars=target_stars,
            check_in=h.check_in, check_out=h.check_out,
            exclude=h.name if exclude_current else None,
        ) or []
        if not candidates:
            return None

        best = min(candidates, key=lambda c: c.get("priceIdr", 1 << 62))
        hotel = HotelSpec(best.get("name", "?"), target_stars, h.city,
                          best.get("area", h.area), h.check_in, h.check_out,
                          int(best.get("priceIdr", 0)))
        return RungCandidate(self.flight_idr + hotel.price_idr, hotel=hotel)


# ── Fixture-backed tool data ─────────────────────────────────────────────────

def fixture_hotels(city, area, stars, exclude=None):
    """Hotel inventory for the search_hotels tool in replay mode.

    Derived from the captured rung candidates rather than a second invented
    dataset, so the tool and the ladder can never disagree about what was
    available."""
    out = []
    for cid, data in (fixtures().get("carts") or {}).items():
        rungs = data.get("rungs") or {}
        flight = int(data.get("flight_idr", 0))
        for rung, name_map in ((config.RUNG_LATERAL, _LATERAL_NAMES),
                               (config.RUNG_TIER_DOWN, _TIER_DOWN_NAMES)):
            total = rungs.get(rung)
            name = name_map.get(cid)
            if total is None or not name:
                continue
            if exclude and name.strip().lower() == exclude.strip().lower():
                continue
            out.append({
                "name": name,
                "stars": stars,
                "area": area,
                "priceIdr": int(total) - flight,
            })
    return out


def fixture_flights(origin, destination):
    """Flight offers for the search_flights tool in replay mode."""
    out = []
    for cid, data in (fixtures().get("carts") or {}).items():
        price = int(data.get("flight_idr", 0))
        if not price:
            continue
        hold = (fixtures().get("hold") or {}).get(cid) or {}
        out.append({
            "carrier": hold.get("carrier", ""),
            "priceIdr": price,
            "offerId": "fixture-" + cid,
            "paymentRequirements": {
                "requires_instant_payment": hold.get("state") != HoldState.ELIGIBLE,
                "payment_required_by": hold.get("expires_at"),
            },
        })
    return out


# ── Hold ─────────────────────────────────────────────────────────────────────

def hold_status(cart_id: str, carrier: str) -> HoldStatus:
    """
    Fixture-backed hold state. The live equivalent lives in hold_manager.py and
    reads payment_requirements off the Duffel offer.
    """
    row: Dict = (fixtures().get("hold") or {}).get(cart_id) or {}
    state = row.get("state", HoldState.NOT_ELIGIBLE)
    note = None
    if state == HoldState.SIMULATED:
        note = "Simulasi pre-authorization - bukan jaminan maskapai."
    elif state == HoldState.ELIGIBLE:
        note = "Harga penerbangan dijamin maskapai. Hotel tetap dihitung ulang saat pembayaran."
    return HoldStatus(state=state, expires_at=row.get("expires_at"),
                      carrier=row.get("carrier", carrier), note=note)
