"""
mcp_server.py — Travel Model Context Protocol (MCP) Server.

Exposes flight, hotel, and weather tool context natively to LLMs.
Uses the official python mcp.server.fastmcp framework.
Can be started via: python -m backend.mcp_server
"""
import sys
import logging
from mcp.server.fastmcp import FastMCP
from . import skyscanner_gds

# Set up logging to stderr only, as stdout is reserved for MCP JSON-RPC messages
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

# Initialize FastMCP Server
mcp = FastMCP("Travel Service Server")

@mcp.tool()
def search_flights(origin: str, destination: str, currency: str, direction: str, total_budget: float = 1000.0, departure_date: str = "") -> str:
    """Query live flights via GDS and returns options matching budget constraints.
    
    Args:
        origin: 3-letter IATA airport code (e.g. CGK, SFO)
        destination: 3-letter IATA airport code (e.g. NRT, LHR)
        currency: 3-letter currency code (e.g. IDR, USD, JPY)
        direction: 'outbound' or 'inbound'
        total_budget: total numeric budget limit
        departure_date: actual trip departure date (ISO YYYY-MM-DD). Leave blank to use default +30/+37 days.
    """
    logger.info(f"[MCP Tool] search_flights tool called for {direction} {origin}->{destination} on {departure_date or 'default date'}")
    options = skyscanner_gds.mock_gds_search_flights(
        origin, destination, currency, direction, total_budget,
        departure_date=departure_date or None
    )
    import json
    return json.dumps(options)

@mcp.tool()
def search_hotels(destination: str, currency: str, total_budget: float = 1000.0, destination_iata: str = "", checkin: str = "", checkout: str = "", num_nights: int = 5) -> str:
    """Query live hotel accommodation options matching target budget and currency.
    
    Args:
        destination: Name of destination city or area (e.g. Tokyo, London)
        currency: 3-letter currency code (e.g. USD, EUR, IDR)
        total_budget: total numeric budget limit
        destination_iata: optional 3-letter IATA city/airport code for precise query
        checkin: actual trip check-in date (ISO YYYY-MM-DD). Leave blank to use default +30 days.
        checkout: actual trip check-out date (ISO YYYY-MM-DD). Leave blank to derive from num_nights.
        num_nights: number of hotel nights (used if checkout not provided, default 5)
    """
    logger.info(f"[MCP Tool] search_hotels tool called for {destination} ({checkin}→{checkout}, {num_nights} nights)")
    options = skyscanner_gds.mock_gds_search_hotels(
        destination, currency, total_budget, destination_iata,
        checkin=checkin or None,
        checkout=checkout or None,
        num_nights=num_nights,
    )
    import json
    return json.dumps(options)

@mcp.tool()
def read_traveler_history(traveler_id: str) -> str:
    """Read one traveler's booking history and their abandoned cart.

    Args:
        traveler_id: seed id, e.g. wf-02
    """
    logger.info(f"[MCP Tool] read_traveler_history for {traveler_id}")
    import json
    from .recovery import mcp_tools
    return json.dumps(mcp_tools.read_traveler_history(traveler_id))


@mcp.tool()
def check_hold_eligibility(cart_id: str, carrier: str, offer_id: str = "") -> str:
    """Check whether a flight fare can be held, and until when. READ-ONLY.

    Reads payment_requirements off the Duffel offer. Covers the FLIGHT only --
    the hotel has no equivalent primitive and re-prices at conversion.

    There is deliberately no create_hold tool: placing a hold is a real write
    against airline inventory and must not fire during a demo.

    Args:
        cart_id: cart identifier, e.g. cart-wf-02
        carrier: operating carrier name
        offer_id: optional Duffel offer id
    """
    logger.info(f"[MCP Tool] check_hold_eligibility for {cart_id}")
    import json
    from .recovery import mcp_tools
    return json.dumps(mcp_tools.check_hold_eligibility(
        cart_id, carrier, offer_id or None))


@mcp.tool()
def get_destination_weather(destination: str) -> str:
    """Fetch live weather metrics and packing advice for target destination.
    
    Args:
        destination: target city name
    """
    logger.info(f"[MCP Tool] get_destination_weather tool called for {destination}")
    try:
        import requests
        # Query wttr.in with ?format=3 for a concise one-line weather summary
        url = f"https://wttr.in/{requests.utils.quote(destination)}?format=3"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        weather = resp.text.strip()
        # Add packing advice dynamically via simple temperature extraction
        import re
        temp_match = re.search(r'([+-]?\d+)(?:°C|°F)', weather)
        advice = "Packing advice: Bring standard seasonal clothing."
        if temp_match:
            temp = int(temp_match.group(1))
            if temp < 10:
                advice = "Packing advice: Cold weather! Bring a heavy winter coat, gloves, and a scarf."
            elif temp < 20:
                advice = "Packing advice: Mild/cool weather. A light jacket or sweater is recommended."
            elif temp > 28:
                advice = "Packing advice: Warm weather. Wear light, breathable clothing and bring sunglasses."
        return f"Weather: {weather}. {advice}"
    except Exception as e:
        logger.error(f"[MCP Tool] wttr.in weather fetch failed ({e}). Falling back to default weather.")
        return f"Weather: Mild, 21°C (70°F) in {destination}. Packing advice: Standard seasonal clothing."

@mcp.tool()
def get_places_of_interest(latitude: float, longitude: float) -> str:
    """Query live Points of Interest (POIs) and attractions matching target coordinates.
    
    Args:
        latitude: Latitude coordinate of target destination
        longitude: Longitude coordinate of target destination
    """
    logger.info(f"[MCP Tool] get_places_of_interest tool called for ({latitude}, {longitude})")
    pois = skyscanner_gds.mock_gds_search_pois(latitude, longitude)
    import json
    return json.dumps(pois)

@mcp.tool()
def curate_itinerary(destination: str, days: int = 5, pois_json: str = "[]", weather: str = "", hotel_name: str = "", budget_remaining: float = 500.0, currency: str = "USD") -> str:
    """Generate a professionally curated day-by-day travel itinerary with time blocks, dining, transport, and cost estimates.
    
    Args:
        destination: Destination city name (e.g. Tokyo, London)
        days: Number of days for the itinerary
        pois_json: JSON string of POIs/attractions near the destination
        weather: Weather forecast text for packing/activity advice
        hotel_name: Name of the booked hotel for proximity-based planning
        budget_remaining: Remaining budget after flights and hotel
        currency: 3-letter currency code (e.g. USD, JPY, EUR)
    """
    import json
    import os
    logger.info(f"[MCP Tool] curate_itinerary called for {destination} ({days} days)")
    
    pois = json.loads(pois_json) if pois_json else []
    poi_names = [p.get("name", "attraction") for p in pois[:8]]
    poi_str = ", ".join(poi_names) if poi_names else "local landmarks and attractions"
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        # Fallback structured itinerary without LLM
        itinerary = []
        for d in range(1, days + 1):
            if d == 1:
                itinerary.append({
                    "day": d,
                    "title": f"Arrival in {destination}",
                    "activities": [
                        {"time": "09:00", "spot": f"{destination} Airport",  "description": f"Arrive at {destination} airport. Take express train or taxi to your hotel.",  "estimated_spend": 20},
                        {"time": "12:00", "spot": hotel_name or "Hotel",     "description": "Check in. Freshen up and rest after your journey.",                          "estimated_spend": 0},
                        {"time": "15:00", "spot": "Neighbourhood Walk",       "description": "Explore the streets around your hotel on foot. Get your bearings.",             "estimated_spend": 10},
                        {"time": "19:00", "spot": "Local Restaurant",         "description": "Dinner at a recommended local restaurant near the hotel.",                      "estimated_spend": 20},
                    ],
                    "tips": "Get a local transit card at the airport for convenience.",
                    "estimated_cost": 50,
                })
            elif d == days:
                itinerary.append({
                    "day": d,
                    "title": "Departure Day",
                    "activities": [
                        {"time": "07:00", "spot": hotel_name or "Hotel",     "description": "Pack bags. Enjoy final breakfast at the hotel or a nearby café.", "estimated_spend": 15},
                        {"time": "10:00", "spot": f"{destination} Airport", "description": "Transfer to the airport. Allow extra time for security.",          "estimated_spend": 15},
                    ],
                    "tips": "Leave 3 hours before international flights for security.",
                    "estimated_cost": 30,
                })
            else:
                poi_idx = (d - 2) % len(poi_names) if poi_names else 0
                poi = poi_names[poi_idx] if poi_names else "local attractions"
                itinerary.append({
                    "day": d,
                    "title": f"Explore {poi}",
                    "activities": [
                        {"time": "09:00", "spot": poi,                 "description": f"Visit {poi}. Allow 2–3 hours for exploration.",                          "estimated_spend": 20},
                        {"time": "12:30", "spot": "Local Restaurant",  "description": "Lunch at a nearby restaurant. Try a local specialty.",                       "estimated_spend": 25},
                        {"time": "14:00", "spot": "Area Sightseeing",  "description": "Continue sightseeing in the surrounding area.",                              "estimated_spend": 15},
                        {"time": "19:00", "spot": "Evening Dining",    "description": f"Return to hotel, freshen up. Evening walk and dinner.\n{weather}",         "estimated_spend": 25},
                    ],
                    "tips": weather if weather else "Check local transport schedules in advance.",
                    "estimated_cost": 85,
                })
        return json.dumps(itinerary)
    
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-flash-latest")
        
        prompt = f"""You are a professional travel curator. Create a detailed {days}-day itinerary for a trip to {destination}.

CONTEXT:
- Hotel: {hotel_name or 'centrally located hotel'}
- Weather forecast: {weather or 'Mild seasonal weather'}
- Budget remaining (after flights/hotel): {currency} {budget_remaining:.0f}
- Top attractions/POIs to include: {poi_str}

REQUIREMENTS:
For each day, return an `activities` array with 4–6 entries. Each entry must have:
- `time`: a 24-hour time string like "09:00"
- `spot`: the specific venue/location name (e.g. "Eiffel Tower", "Café de Flore")
- `description`: 1–2 sentences describing the activity, including transport instructions where relevant
- `estimated_spend`: numeric cost in {currency} for that single activity/stop (integer, no symbol)

Also include:
- `title`: a catchy day title
- `tips`: one practical tip (transport, dress code, pre-booking)
- `estimated_cost`: daily total spend (sum of all estimated_spend values)

Make it feel like a premium travel magazine itinerary:
- Day 1 must be arrival; last day must be departure
- Weave real POIs naturally; include specific restaurant names and local dishes
- Include transport (e.g. "Take the Métro Line 6 to Trocadéro, 20 min, ~€2")

Return ONLY a raw JSON array (no markdown, no ```):
[
  {{
    "day": 1,
    "title": "Arrival & First Impressions",
    "activities": [
      {{"time": "10:00", "spot": "{destination} Airport", "description": "Clear customs and take the express train to the city centre.", "estimated_spend": 15}},
      {{"time": "13:00", "spot": "{hotel_name or 'Hotel'}", "description": "Check in and refresh. Drop bags and head out.", "estimated_spend": 0}},
      {{"time": "15:00", "spot": "Nearby Landmark", "description": "Short stroll to get your bearings.", "estimated_spend": 0}},
      {{"time": "19:30", "spot": "Local Restaurant", "description": "Dinner — try the local specialty dish.", "estimated_spend": 35}}
    ],
    "tips": "Get a transit card at the airport.",
    "estimated_cost": 50
  }},
  ...
]"""
        
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("\n", 1)[0].strip()
        if text.startswith("json"):
            text = text[4:].strip()
        
        itinerary = json.loads(text)
        if isinstance(itinerary, list) and len(itinerary) > 0:
            logger.info(f"[MCP Tool] Curated {len(itinerary)}-day itinerary for {destination}")
            return json.dumps(itinerary)
    except Exception as e:
        logger.error(f"[MCP Tool] curate_itinerary error: {e}")
    
    # Fallback
    return json.dumps([
        {"day": d, "title": f"Day {d} in {destination}", "morning": "Morning activities", "afternoon": "Afternoon exploration", "evening": "Evening dining", "tips": "Check local guides", "estimated_cost": 80}
        for d in range(1, days + 1)
    ])

if __name__ == "__main__":
    # Start the stdio MCP server
    logger.info("[MCP] Starting Travel Service stdio MCP server...")
    mcp.run()

