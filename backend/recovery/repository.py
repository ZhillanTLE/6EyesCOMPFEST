"""
repository.py — Loads seed travelers and their abandoned carts.

Behind the read_traveler_history MCP tool. Post-penyisihan this same module is
repointed at a live profile store and no agent prompt changes, which is the
whole architectural argument for putting MCP in front of it.
"""
from __future__ import annotations

import json
import os
from typing import Dict, List, Optional, Tuple

from .schemas import AbandonedCart, FlightSpec, HotelSpec, TravelerHistory

SEED_PATH = os.path.join(os.path.dirname(__file__), "seed", "travelers.json")

_cache: Optional[dict] = None


def _load() -> dict:
    global _cache
    if _cache is None:
        with open(SEED_PATH, encoding="utf-8") as fh:
            _cache = json.load(fh)
    return _cache


def _history(row: dict) -> TravelerHistory:
    return TravelerHistory(
        traveler_id=row["traveler_id"],
        name=row["name"],
        booking_count=row["booking_count"],
        usual_spend=row["usual_spend"],
        campaign_share=row["campaign_share"],
        avg_hotel_stars=row.get("avg_hotel_stars"),
        premium_cabin_share=row.get("premium_cabin_share"),
    )


def _cart(row: dict, flight_idr: int = 0, hotel_idr: int = 0) -> AbandonedCart:
    c, f, h = row["cart"], row["cart"]["flight"], row["cart"]["hotel"]
    return AbandonedCart(
        cart_id=c["cart_id"],
        traveler_id=row["traveler_id"],
        flight=FlightSpec(
            carrier=f["carrier"], origin=f["origin"], destination=f["destination"],
            depart_date=f["depart_date"], return_date=f.get("return_date"),
            cabin=f["cabin"], passengers=f["passengers"], price_idr=flight_idr,
        ),
        hotel=HotelSpec(
            name=h["name"], stars=h["stars"], city=h["city"], area=h["area"],
            check_in=h["check_in"], check_out=h["check_out"], price_idr=hotel_idr,
        ),
        abandoned_hours_ago=c["abandoned_hours_ago"],
    )


def all_travelers() -> List[dict]:
    return list(_load()["travelers"])


def reference_spend() -> List[float]:
    """The distribution the percentile tier is taken against."""
    field = _load().get("reference_distribution_field", "usual_spend")
    return [t[field] for t in _load()["travelers"]]


def get(traveler_id: str) -> Tuple[TravelerHistory, dict]:
    for row in _load()["travelers"]:
        if row["traveler_id"] == traveler_id:
            return _history(row), row
    raise KeyError("unknown traveler " + repr(traveler_id))


def build_cart(row: dict, flight_idr: int, hotel_idr: int) -> AbandonedCart:
    """Cart with prices attached. Prices always come from outside the seed."""
    return _cart(row, flight_idr, hotel_idr)


def queue() -> List[Dict]:
    """
    The browse list. Deliberately withholds tier and campaign share: those are
    the Classifier's conclusions, and printing them on the card the analyst is
    about to click would let the pipeline appear to conclude what was already
    on screen.
    """
    out = []
    for row in _load()["travelers"]:
        c, f, h = row["cart"], row["cart"]["flight"], row["cart"]["hotel"]
        out.append({
            "traveler_id": row["traveler_id"],
            "cart_id": c["cart_id"],
            "name": row["name"],
            "booking_count": row["booking_count"],
            "route": "{} - {}".format(f["origin"], f["destination"]),
            "carrier": f["carrier"],
            "cabin": f["cabin"],
            "passengers": f["passengers"],
            "depart_date": f["depart_date"],
            "return_date": f.get("return_date"),
            "hotel_name": h["name"],
            "hotel_stars": h["stars"],
            "hotel_city": h["city"],
            "check_in": h["check_in"],
            "check_out": h["check_out"],
            "abandoned_hours_ago": c["abandoned_hours_ago"],
        })
    return out
