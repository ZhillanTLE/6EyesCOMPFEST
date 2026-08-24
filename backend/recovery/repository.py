"""
repository.py — Loads seed travelers and their abandoned carts.

Behind the read_traveler_history MCP tool. Post-penyisihan this same module is
repointed at a live profile store and no agent prompt changes, which is the
whole architectural argument for putting MCP in front of it.

Seed JSON is camelCase per the data contract; Python locals stay snake_case.
"""
from __future__ import annotations

import json
import os
from typing import Dict, List, Optional, Tuple

from . import config, tiers
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
        traveler_id=row["travelerId"],
        name=row["name"],
        booking_count=row["bookings"],
        usual_spend=row["usualSpend"],
        campaign_share=row["campaignShare"],
        avg_hotel_stars=row.get("avgStars"),
        premium_cabin_share=row.get("premiumCabinShare"),
    )


def all_travelers() -> List[dict]:
    return list(_load()["travelers"])


def traveler_ids() -> List[str]:
    # Just the ids, for validating a --cart argument. Exists so callers that
    # only need to check an id never write `for ... in all_travelers()` -- that
    # is the shape the scope check flags as a bulk runner, and the right
    # response is to not write it rather than to exempt it.
    return [t["travelerId"] for t in _load()["travelers"]]


def reference_spend() -> List[float]:
    """The distribution the percentile tier is taken against."""
    field = _load().get("referenceDistributionField", "usualSpend")
    return [t[field] for t in _load()["travelers"]]


def get(traveler_id: str) -> Tuple[TravelerHistory, dict]:
    for row in _load()["travelers"]:
        if row["travelerId"] == traveler_id:
            return _history(row), row
    raise KeyError("unknown traveler " + repr(traveler_id))


def cart_value(row: dict) -> int:
    """p_0: what the cart cost at the moment it was abandoned."""
    c = row["cart"]
    return int(c["flight"]["valueIdr"]) + int(c["hotel"]["valueIdr"])


def build_cart(row: dict) -> AbandonedCart:
    """
    The abandoned cart, priced as the traveler left it.

    These are abandonment prices, not a live quote. Re-quoting to find p_k is
    the Searcher's job; p_0 is history and does not move underneath it.
    """
    c, f, h = row["cart"], row["cart"]["flight"], row["cart"]["hotel"]
    flight_idr = int(f["valueIdr"])
    hotel_idr = int(h["valueIdr"])
    return AbandonedCart(
        cart_id=c["cartId"],
        traveler_id=row["travelerId"],
        flight=FlightSpec(
            carrier=f["carrier"], origin=f["origin"], destination=f["destination"],
            depart_date=f["departDate"], return_date=f.get("returnDate"),
            cabin=f["cabin"], passengers=f["passengers"], price_idr=flight_idr,
        ),
        hotel=HotelSpec(
            name=h["name"], stars=h["stars"], city=h["city"], area=h["area"],
            check_in=h["checkIn"], check_out=h["checkOut"], price_idr=hotel_idr,
        ),
        abandoned_hours_ago=c["abandonedHoursAgo"],
    )


def queue() -> List[Dict]:
    """
    The browse list.

    Carries a PROVISIONAL tier estimate and the raw campaign share -- not the
    Classifier's verdict. The distinction is the point: campaign share is raw
    history and the estimate is a deterministic percentile lookup, both cheap
    and available before any inference runs. What the Classifier produces is a
    reasoned tier that can differ from the estimate and can weigh signals a
    single percentile cannot.
    
    Showing the estimate is what gives a judge a hypothesis to test the model
    against. Without it there is nothing to compare the output to, and the
    fair question becomes why Gemini is in the loop at all. The UI must label
    it provisional so the difference reads on screen.
    """
    spend = reference_spend()
    out = []
    for row in _load()["travelers"]:
        c, f, h = row["cart"], row["cart"]["flight"], row["cart"]["hotel"]
        history = _history(row)
        cold = history.is_cold_start
        if cold:
            # No monetary history, so the estimate comes from the cart itself.
            estimate = tiers.tier_from_cart_proxy_fields(f["cabin"], h["stars"])
        else:
            estimate = tiers.tier_from_percentile(
                tiers.percentile_rank(history.usual_spend, spend))
        out.append({
            "travelerId": row["travelerId"],
            "cartId": c["cartId"],
            "name": row["name"],
            "bookings": row["bookings"],
            "tierEstimate": estimate,
            "tierEstimateLabel": "Cold-start" if cold else estimate,
            "isColdStart": cold,
            "campaignShare": row["campaignShare"],
            "route": "{} \u2192 {}".format(f["origin"], f["destination"]),
            "carrier": f["carrier"],
            "cabin": f["cabin"],
            "passengers": f["passengers"],
            "departDate": f["departDate"],
            "returnDate": f.get("returnDate"),
            "hotelName": h["name"],
            "hotelStars": h["stars"],
            "hotelCity": h["city"],
            "checkIn": h["checkIn"],
            "checkOut": h["checkOut"],
            "abandonedHoursAgo": c["abandonedHoursAgo"],
            "cartValueIdr": cart_value(row),
            # Browse-card signals. Read-only history, already loaded above --
            # null on cold start rather than zero, for the same reason
            # campaignShare is: a traveler with no history has no average, and
            # a fabricated one would read as a real measurement.
            "usualSpendIdr": None if cold else history.usual_spend,
            "avgStars": None if cold else row.get("avgStars"),
        })
    return out
