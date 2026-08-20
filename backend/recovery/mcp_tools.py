"""
mcp_tools.py — The tool contract the agents reason through.

Paper section 5.1: the agents do not call API clients directly. They call four
tools -- read_traveler_history, search_flights, search_hotels,
check_hold_eligibility -- and the data source behind each can be swapped
without touching a prompt or a line of agent logic.

`create_hold` IS DELIBERATELY ABSENT and must never be added. Holding an offer
is a real write against airline inventory; a demo clicking through six carts
must not place six holds. Eligibility is read-only and safe to call.

TWO CALL PATHS, ONE IMPLEMENTATION. The functions below are the single source
of truth. backend/mcp_server.py registers them with FastMCP so a real MCP
client can call them over stdio, and the synchronous recovery pipeline calls
the same functions in-process.

That in-process path is a deliberate choice, not a shortcut. Spawning an MCP
subprocess per cart would add roughly a second of process startup to every
click and introduce a failure mode with no upside: the architectural claim the
paper makes is about the *contract* -- that swapping the data source behind a
tool changes no prompt -- and sharing one implementation is what makes that
claim true. Set WINDFALL_MCP=stdio to route through a real MCP session instead
and prove the contract holds across the boundary.
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional

from . import hold_manager, providers, repository
from .schemas import HoldState


def use_stdio() -> bool:
    """Route tool calls through a real MCP stdio session rather than in-process."""
    return os.environ.get("WINDFALL_MCP", "").strip().lower() == "stdio"


# ── read_traveler_history ────────────────────────────────────────────────────

def read_traveler_history(traveler_id: str) -> Dict:
    """
    Booking history for one traveler.

    Reads the local seed today. Post-penyisihan this points at a live profile
    store and nothing upstream changes -- that substitution is the entire
    reason the tool boundary exists.

    campaignShare is null for a traveler with too little history to measure it.
    It is never estimated, and never filled in with a plausible-looking number.
    """
    history, row = repository.get(traveler_id)
    return {
        "travelerId": history.traveler_id,
        "name": history.name,
        "bookings": history.booking_count,
        "usualSpend": history.usual_spend,
        "campaignShare": history.campaign_share,
        "avgStars": history.avg_hotel_stars,
        "premiumCabinShare": history.premium_cabin_share,
        "isColdStart": history.is_cold_start,
        "cart": row["cart"],
    }


# ── search_hotels ────────────────────────────────────────────────────────────

def search_hotels(city: str, area: str, stars: int, check_in: str,
                  check_out: str, exclude: Optional[str] = None) -> List[Dict]:
    """
    Hotel inventory at a given star rating, for the rebuild ladder.

    `exclude` drops the property already in the cart, which is what makes a
    lateral swap lateral rather than a re-price of the same room.
    """
    if providers.use_fixtures():
        return providers.fixture_hotels(city, area, stars, exclude)

    from .. import skyscanner_gds
    results = skyscanner_gds.mock_gds_search_hotels(city, "IDR", 10 ** 12, "")
    out = []
    for r in results or []:
        name = r.get("name") or r.get("hotel_name") or ""
        if exclude and name.strip().lower() == exclude.strip().lower():
            continue
        out.append({
            "name": name,
            "stars": r.get("stars", stars),
            "area": r.get("area", area),
            "priceIdr": int(r.get("price", 0) or 0),
        })
    return out


# ── search_flights ───────────────────────────────────────────────────────────

def search_flights(origin: str, destination: str, depart_date: str,
                   cabin: str = "economy") -> List[Dict]:
    """
    Flight offers.

    The rebuild ladder never swaps the flight -- a Hold Order is held against
    one specific offer -- so this exists to price the original cart and to
    re-quote it on the re-price rung, not to shop for alternatives.
    """
    if providers.use_fixtures():
        return providers.fixture_flights(origin, destination)

    from .. import skyscanner_gds
    results = skyscanner_gds.mock_gds_search_flights(
        origin, destination, "IDR", "outbound", 10 ** 12,
        departure_date=depart_date)
    return [{
        "carrier": r.get("airline", ""),
        "priceIdr": int(r.get("price", 0) or 0),
        "offerId": r.get("offer_id"),
        "paymentRequirements": r.get("payment_requirements"),
    } for r in (results or [])]


# ── check_hold_eligibility ───────────────────────────────────────────────────

def check_hold_eligibility(cart_id: str, carrier: str,
                           offer_id: Optional[str] = None) -> Dict:
    """
    READ-ONLY. Can this fare be held, and until when?

    Reads `payment_requirements` off a Duffel offer:
      requires_instant_payment == False  ->  the offer can be held
      payment_required_by                ->  the ONLY legitimate countdown source

    Nothing here writes. There is no create_hold, by design.

    Covers the FLIGHT only. The hotel has no equivalent primitive and re-prices
    at conversion; callers must say so rather than implying the cart is frozen.
    """
    return hold_manager.as_tool_payload(
        hold_manager.evaluate(cart_id, carrier, offer=None))


TOOLS = {
    "read_traveler_history": read_traveler_history,
    "search_flights": search_flights,
    "search_hotels": search_hotels,
    "check_hold_eligibility": check_hold_eligibility,
}


def call_tool(name: str, **kwargs):
    """
    Dispatch by name, so the call site reads as a tool call either way.

    WINDFALL_MCP=stdio routes through a real MCP client session instead of
    calling in-process. Same tool, same arguments, same result -- which is the
    point: it demonstrates that the contract holds across the process boundary
    rather than asking anyone to take that on trust.

    Not the default. Each call spawns `python -m backend.mcp_server` and pays
    roughly a second of process startup, which is a poor trade for every cart
    click when the implementation is shared either way.
    """
    if name not in TOOLS:
        raise KeyError("no such tool: {} (create_hold is deliberately absent)".format(name))
    if use_stdio():
        return _call_over_stdio(name, kwargs)
    return TOOLS[name](**kwargs)


def _call_over_stdio(name: str, arguments: dict):
    """
    Call the tool through a real MCP stdio session.

    Synchronous from the caller's perspective: asyncio.run drives the session
    to completion inside the request that triggered it, so this stays within
    one request/response cycle and adds no background work.
    """
    import asyncio
    import json as _json
    import sys

    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def _run():
        params = StdioServerParameters(
            command=sys.executable, args=["-m", "backend.mcp_server"], env=dict(os.environ))
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(name, arguments)
                text = "".join(
                    getattr(c, "text", "") for c in (result.content or []))
                return _json.loads(text) if text else None

    return asyncio.run(_run())
