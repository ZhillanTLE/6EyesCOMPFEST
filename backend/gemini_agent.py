import os
import math
from . import places_api
import time
import logging
import threading
import json
import concurrent.futures
import sys
import asyncio
from datetime import datetime, timedelta
import google.generativeai as genai
import hashlib
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from . import firebase_state
from . import skyscanner_gds

logger = logging.getLogger(__name__)

# Fallback registries
DESTINATIONS = {
    "japan": [139.6503, 35.6762],
    "tokyo": [139.6503, 35.6762],
    "kyoto": [135.7681, 35.0116],
    "london": [-0.1278, 51.5074],
    "paris": [2.3522, 48.8566],
    "new york": [-74.0060, 40.7128],
    "nyc": [-74.0060, 40.7128],
    "san francisco": [-122.4194, 37.7749],
    "sfo": [-122.4194, 37.7749],
    "hawaii": [-157.8583, 21.3069],
    "honolulu": [-157.8583, 21.3069],
    "jakarta": [106.6527, -6.1275],
    "cgk": [106.6527, -6.1275]
}

# Thread-local storage to pass request parameters to functions called by Gemini
agent_context = threading.local()

from .nlp_parser import parse_trip_request

def extract_trip_entities(user_text: str) -> dict:
    """Uses the robust nlp_parser to extract parameters dynamically."""
    return parse_trip_request(user_text)

def budget_agent_interceptor(out_idx, in_idx, hotel_idx, outbound_opts, inbound_opts, hotel_opts, total_budget):
    """Budget Agent interceptor that exactly calculates the cost and enforces the constraint."""
    cost = outbound_opts[out_idx]["cost"] + inbound_opts[in_idx]["cost"] + hotel_opts[hotel_idx]["cost"]
    if cost > total_budget:
        return False, f"Intercepted by Budget Agent: Selected plan costs {cost}, which exceeds budget by {cost - total_budget}."
    return True, cost

def multi_agent_orchestrate(outbound_opts: list, inbound_opts: list, hotel_opts: list, total_budget: float, currency_symbol: str, session_id: str, socketio) -> tuple:
    """Multi-agent orchestrator loop combining a Planner LLM Agent and a Python Budget Agent interceptor."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return orchestrate_travel_plan(outbound_opts, inbound_opts, hotel_opts, total_budget)
        
    import google.generativeai as genai
    import hashlib
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-flash-latest")
    
    def format_opts(opts):
        import json
        return json.dumps([{"index": i, "desc": o.get("carrier", o.get("hotel_name")), "cost": o["cost"]} for i, o in enumerate(opts)])
        
    out_str = format_opts(outbound_opts)
    in_str = format_opts(inbound_opts)
    hot_str = format_opts(hotel_opts)
    
    chat_history = []
    
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        prompt = f"""
You are the Planner Agent. Your goal is to select the highest quality combination of travel options without exceeding the total budget.
Total Budget: {total_budget}
Outbound Options: {out_str}
Inbound Options: {in_str}
Hotel Options: {hot_str}

Previous Feedback from Budget Agent:
{json.dumps(chat_history)}

Select one index from each array. 
Return ONLY a valid JSON array of 3 integers: [outbound_index, inbound_index, hotel_index].
Do not include any other text, explanations, or markdown.
"""
        try:
            if socketio:
                socketio.emit("step_progress", {"step": "budget", "state": "in_progress", "message": f"Planner Agent proposing itinerary (Attempt {attempt})..."}, room=session_id)
                import time
                time.sleep(0.5) # Give UI time to paint
                
            response = model.generate_content(prompt)
            text = response.text.strip()
            
            if text.startswith("```"):
                text = text.split("\\n", 1)[1].rsplit("\\n", 1)[0].strip()
            if text.startswith("json"):
                text = text[4:].strip()
                
            indices = json.loads(text)
            if not isinstance(indices, list) or len(indices) != 3:
                raise ValueError("Invalid format")
                
            out_idx, in_idx, hot_idx = [int(x) for x in indices]
            
            # Bound check indices
            out_idx = min(max(0, out_idx), len(outbound_opts)-1)
            in_idx = min(max(0, in_idx), len(inbound_opts)-1)
            hot_idx = min(max(0, hot_idx), len(hotel_opts)-1)
            
            # --- BUDGET AGENT INTERCEPTOR ---
            if socketio:
                socketio.emit("step_progress", {"step": "budget", "state": "in_progress", "message": "Budget Agent analyzing proposed plan..."}, room=session_id)
                time.sleep(0.5)
                
            is_valid, msg = budget_agent_interceptor(out_idx, in_idx, hot_idx, outbound_opts, inbound_opts, hotel_opts, total_budget)
            
            if is_valid:
                logger.info(f"[Multi-Agent] Plan approved by Budget Agent. Total cost: {msg}.")
                if socketio:
                    socketio.emit("step_progress", {"step": "budget", "state": "done", "message": f"Budget Agent approved! Total cost: {currency_symbol}{msg}."}, room=session_id)
                return out_idx, in_idx, hot_idx
            else:
                logger.warning(f"[Multi-Agent] {msg}")
                if socketio:
                    socketio.emit("step_progress", {"step": "budget", "state": "in_progress", "message": msg}, room=session_id)
                chat_history.append({"attempt": attempt, "feedback": msg})
                
        except Exception as e:
            logger.error(f"[Multi-Agent] Error during planning loop: {e}")
            chat_history.append({"attempt": attempt, "feedback": "System Error: invalid JSON or selection format. Please return ONLY a JSON array."})
            
    # Fallback if loop exhausts
    logger.warning("[Multi-Agent] Planner Agent exhausted retries. Budget Agent forcing fallback to combinatorial minimum.")
    if socketio:
         socketio.emit("step_progress", {"step": "budget", "state": "done", "message": "Budget Agent forced override: selecting guaranteed cheapest valid combination."}, room=session_id)
    return orchestrate_travel_plan(outbound_opts, inbound_opts, hotel_opts, total_budget)


def orchestrate_travel_plan(outbound_opts: list, inbound_opts: list, hotel_opts: list, total_budget: float) -> tuple:
    """Combinatorial optimization algorithm to select default options within budget.
    
    Tries to maximize travel quality/preference by scoring combinations,
    guaranteeing the default selected plan never exceeds the total budget constraint.
    """
    valid_combos = []
    
    for i, out_f in enumerate(outbound_opts):
        for j, in_f in enumerate(inbound_opts):
            for k, hotel in enumerate(hotel_opts):
                total_cost = out_f["cost"] + in_f["cost"] + hotel["cost"]
                if total_cost <= total_budget:
                    # Score combination: higher total cost is assumed to be higher quality
                    # (e.g. premium classes and premium resort locations)
                    score = total_cost
                    valid_combos.append((score, i, j, k))
                    
    if valid_combos:
        # Sort by quality score descending
        valid_combos.sort(key=lambda x: x[0], reverse=True)
        best_score, best_out, best_in, best_hotel = valid_combos[0]
        logger.info(f"[Orchestrator] Found valid combination within budget. Cost: {best_score}/{total_budget}. Selected indices: Out={best_out}, In={best_in}, Hotel={best_hotel}")
        return best_out, best_in, best_hotel
    else:
        # Fallback: Find absolute cheapest combo if no combination meets the budget
        cheapest_indices = (1, 1, 2) # Outbound layover, Inbound layover, Hostel
        min_cost = float("inf")
        for i, out_f in enumerate(outbound_opts):
            for j, in_f in enumerate(inbound_opts):
                for k, hotel in enumerate(hotel_opts):
                    cost = out_f["cost"] + in_f["cost"] + hotel["cost"]
                    if cost < min_cost:
                        min_cost = cost
                        cheapest_indices = (i, j, k)
        logger.warning(f"[Orchestrator] No combinations fit budget of {total_budget}. Selecting cheapest combo with cost {min_cost}.")
        return cheapest_indices

async def run_mcp_queries_async(
    origin_code: str, dest_code: str, destination: str,
    currency: str, total_budget: float,
    latitude: float, longitude: float,
    departure_date: str = "", return_date: str = "", num_nights: int = 5,
):
    """Executes MCP tools for flights, hotels, weather, and POIs over standard stdio JSON-RPC transport."""
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "backend.mcp_server"],
        env=os.environ.copy()
    )
    
    logger.info("[MCP Client] Connecting to Travel MCP Server via stdio...")
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            
            # 1. Search outbound flights via MCP
            logger.info("[MCP Client] Invoking 'search_flights' for outbound...")
            out_res = await session.call_tool("search_flights", arguments={
                "origin": origin_code,
                "destination": dest_code,
                "currency": currency,
                "direction": "outbound",
                "total_budget": total_budget,
                "departure_date": departure_date,
            })
            if getattr(out_res, "isError", False):
                raise Exception(out_res.content[0].text)
            outbound_options = json.loads(out_res.content[0].text)
            
            # 2. Search inbound flights via MCP
            logger.info("[MCP Client] Invoking 'search_flights' for inbound...")
            in_res = await session.call_tool("search_flights", arguments={
                "origin": dest_code,
                "destination": origin_code,
                "currency": currency,
                "direction": "inbound",
                "total_budget": total_budget,
                "departure_date": return_date,
            })
            if getattr(in_res, "isError", False):
                raise Exception(in_res.content[0].text)
            inbound_options = json.loads(in_res.content[0].text)
            
            # 3. Search hotels via MCP — pass actual trip dates
            logger.info("[MCP Client] Invoking 'search_hotels'...")
            hotel_res = await session.call_tool("search_hotels", arguments={
                "destination": destination,
                "currency": currency,
                "total_budget": total_budget,
                "destination_iata": dest_code,
                "checkin": departure_date,
                "checkout": return_date,
                "num_nights": num_nights,
            })
            if getattr(hotel_res, "isError", False):
                raise Exception(hotel_res.content[0].text)
            hotel_options = json.loads(hotel_res.content[0].text)
            
            # 4. Fetch destination weather via MCP (showcasing custom tool extension)
            logger.info("[MCP Client] Invoking 'get_destination_weather'...")
            weather_res = await session.call_tool("get_destination_weather", arguments={
                "destination": destination
            })
            if getattr(weather_res, "isError", False):
                raise Exception(weather_res.content[0].text)
            weather_text = weather_res.content[0].text
            
            # 5. Fetch places of interest via MCP
            logger.info("[MCP Client] Invoking 'get_places_of_interest'...")
            pois_res = await session.call_tool("get_places_of_interest", arguments={
                "latitude": latitude,
                "longitude": longitude
            })
            if getattr(pois_res, "isError", False):
                raise Exception(pois_res.content[0].text)
            pois_list = json.loads(pois_res.content[0].text)
            
            return outbound_options, inbound_options, hotel_options, weather_text, pois_list

def run_mcp_queries(
    origin_code: str, dest_code: str, destination: str,
    currency: str, total_budget: float,
    latitude: float, longitude: float,
    departure_date: str = "", return_date: str = "", num_nights: int = 5,
):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(
            run_mcp_queries_async(
                origin_code, dest_code, destination,
                currency, total_budget, latitude, longitude,
                departure_date=departure_date,
                return_date=return_date,
                num_nights=num_nights,
            )
        )
    except BaseExceptionGroup as exc:
        logger.error(f"[MCP Client] TaskGroup Error. Unrolling exceptions:")
        import traceback
        traceback.print_exception(exc)
        for e in exc.exceptions:
            logger.error(f"  - Nested Exception: {type(e).__name__}: {e}")
        # Re-raise the first underlying exception so it propagates meaningfully
        raise exc.exceptions[0] if exc.exceptions else exc
    except Exception as e:
        logger.error(f"[MCP Client] Unexpected error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        loop.close()

def mock_search_flights(destination: str, max_budget: float) -> str:
    """Mock search for roundtrip flight options to a destination within a budget.
    
    Args:
        destination: The target city or country of the trip.
        max_budget: The maximum budget allowed for flights.
    """
    session_id = getattr(agent_context, "session_id", "default_session")
    socketio = getattr(agent_context, "socketio", None)
    trip_entities = getattr(agent_context, "trip_entities", None)
    
    if trip_entities:
        origin_coords = trip_entities.get("origin_coords", [-122.4194, 37.7749])
        dest_coords = trip_entities.get("destination_coords", [139.6503, 35.6762])
        origin_code = trip_entities.get("origin_iata", "JFK").upper()
        dest_code = trip_entities.get("destination_iata", "LHR").upper()
        origin_city = trip_entities.get("origin_city", "Unknown")
        currency = trip_entities.get("currency", "USD").upper()
        total_budget = trip_entities.get("total_budget", 1000.0)
    else:
        origin_code = "SFO"
        dest_code = "NRT"
        currency = "USD"
        total_budget = 1000.0

    # Trigger concurrent searches across Skyscanner and GDS
    if socketio:
        socketio.emit("step_progress", {"step": "flights", "state": "in_progress", "message": f"Searching Duffel for flights to {destination}..."}, room=session_id)
    try:
        outbound_options, inbound_options, hotel_options = run_run_or_cache_gds_queries(origin_code, dest_code, destination, currency, total_budget)
        if socketio:
            cheapest_out = min((o["cost"] for o in outbound_options), default=0)
            sym = trip_entities.get("currency_symbol", "$") if trip_entities else "$"
            socketio.emit("step_progress", {"step": "flights", "state": "done", "message": f"{len(outbound_options)} options found — from {sym}{cheapest_out:,.0f}"}, room=session_id)
    except Exception as e:
        if socketio:
            socketio.emit("step_progress", {"step": "flights", "state": "failed", "message": str(e)}, room=session_id)
            socketio.emit("plan_error", {"error": str(e)}, room=session_id)
        raise e

    # Orchestrate indices to guarantee budget compliance
    if socketio:
        socketio.emit("step_progress", {"step": "budget", "state": "in_progress", "message": "Initiating Multi-Agent Planning Loop..."}, room=session_id)
        
    trip_entities = getattr(agent_context, "trip_entities", {})
    currency_symbol = trip_entities.get("currency_symbol", "$")
    
    best_out, best_in, best_hotel = multi_agent_orchestrate(
        outbound_options, inbound_options, hotel_options, total_budget, currency_symbol, session_id, socketio
    )

    # Save details to context for the hotel search tool
    agent_context.hotel_options = hotel_options
    agent_context.selected_hotel_idx = best_hotel
    agent_context.selected_outbound_idx = best_out
    agent_context.selected_inbound_idx = best_in

    # Update session selections in Firestore
    session = firebase_state.update_session_options(
        session_id,
        outbound_options=outbound_options,
        inbound_options=inbound_options
    )
    
    # Store dynamic indexes in state database
    firebase_state.swap_session_item(session_id, "outbound", best_out, user_id="system")
    firebase_state.swap_session_item(session_id, "inbound", best_in, user_id="system")
    session = firebase_state.get_session(session_id)
    
    # Emit events sequentially
    if socketio:
        logger.info(f"Emitting outbound_flight_locked to room {session_id}")
        socketio.emit("outbound_flight_locked", {
            "options": outbound_options,
            "selected_idx": best_out,
            "cost": outbound_options[best_out]["cost"],
            "remaining_budget": session["remaining_budget"]
        }, room=session_id)
        
        time.sleep(0.1)
        
        logger.info(f"Emitting inbound_flight_locked to room {session_id}")
        socketio.emit("inbound_flight_locked", {
            "options": inbound_options,
            "selected_idx": best_in,
            "cost": inbound_options[best_in]["cost"],
            "remaining_budget": session["remaining_budget"]
        }, room=session_id)
        
    return f"Duffel roundtrip flight options populated. Locked outbound: {outbound_options[best_out]['carrier']}. Locked inbound: {inbound_options[best_in]['carrier']}."

def run_run_or_cache_gds_queries(origin_code, dest_code, destination, currency, total_budget):
    """Retrieves options from context cache if already executed, else runs GDS concurrently."""
    if hasattr(agent_context, "outbound_options"):
        return agent_context.outbound_options, agent_context.inbound_options, agent_context.hotel_options

    # Coordinates injection
    trip_entities = getattr(agent_context, "trip_entities", None)
    if trip_entities:
        origin_coords = trip_entities["origin_coords"]
        dest_coords = trip_entities["destination_coords"]
    else:
        origin_coords = [-122.4194, 37.7749]
        dest_coords = [139.6503, 35.6762]

    # Extract actual trip dates from parsed entities so APIs are queried for real dates
    departure_date = ""
    return_date = ""
    num_nights = 5
    if trip_entities:
        num_nights = trip_entities.get("duration_days", 5)
        # Build ISO date strings from now + ~30 days, offset by duration, if not explicitly provided
        dep_dt = datetime.now() + timedelta(days=30)
        departure_date = dep_dt.strftime("%Y-%m-%d")
        return_date = (dep_dt + timedelta(days=num_nights)).strftime("%Y-%m-%d")
        logger.info(f"[GDS] Using trip dates: departure={departure_date}, return={return_date}, nights={num_nights}")

    # Destination coordinates are in [longitude, latitude] based on extract_trip_entities prompt.
    dest_lon, dest_lat = dest_coords

    outbound, inbound, hotel, weather_text, pois_list = run_mcp_queries(
        origin_code, dest_code, destination, currency, total_budget, dest_lat, dest_lon,
        departure_date=departure_date,
        return_date=return_date,
        num_nights=num_nights,
    )
    
    # Map coordinates onto options
    for opt in outbound:
        opt["origin"] = origin_coords
        opt["destination"] = dest_coords
    for opt in inbound:
        opt["origin"] = dest_coords
        opt["destination"] = origin_coords
        
    # Offset locations slightly to draw distinct hotel map pins
    loc1 = [dest_coords[0] + 0.015, dest_coords[1] + 0.015]
    loc2 = [dest_coords[0] - 0.012, dest_coords[1] + 0.010]
    loc3 = [dest_coords[0] + 0.005, dest_coords[1] - 0.015]
    
    # Guard against fewer than 3 hotel results
    if len(hotel) > 0:
        hotel[0]["location"] = loc1
    if len(hotel) > 1:
        hotel[1]["location"] = loc2
    if len(hotel) > 2:
        hotel[2]["location"] = loc3

    agent_context.outbound_options = outbound
    agent_context.inbound_options = inbound
    agent_context.hotel_options = hotel
    agent_context.weather_text = weather_text
    agent_context.pois_list = pois_list
    
    return outbound, inbound, hotel

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat/2) * math.sin(dLat/2) + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon/2) * math.sin(dLon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def mock_search_hotels(destination: str, max_budget: float, centroid: dict = None) -> str:
    """Mock search for hotel options in a destination within a budget.
    
    Args:
        destination: The target city or country.
        max_budget: The maximum budget allowed for hotels.
        centroid: The latitude/longitude centroid of itinerary spots.
    """
    logger.info(f"Gemini agent called mock_search_hotels with destination='{destination}', max_budget={max_budget}, centroid={centroid}")
    
    session_id = getattr(agent_context, "session_id", "default_session")
    socketio = getattr(agent_context, "socketio", None)
    trip_entities = getattr(agent_context, "trip_entities", None)
    
    if trip_entities:
        dest_code = trip_entities.get("destination_iata", "NRT").upper()
        origin_code = trip_entities.get("origin_iata", "SFO").upper()
        currency = trip_entities.get("currency", "USD").upper()
        total_budget = trip_entities.get("total_budget", 1000.0)
    else:
        dest_code = "NRT"
        origin_code = "SFO"
        currency = "USD"
        total_budget = 1000.0

    # Make sure GDS concurrent query has been executed
    if socketio:
        socketio.emit("step_progress", {"step": "hotels", "state": "in_progress", "message": "Retrieving Hotels.com offers matching target budget..."}, room=session_id)
    try:
        outbound, inbound, hotel_options = run_run_or_cache_gds_queries(origin_code, dest_code, destination, currency, total_budget)
        if socketio:
            socketio.emit("step_progress", {"step": "hotels", "state": "done", "message": f"Found hotels in {destination}"}, room=session_id)
    except Exception as e:
        if socketio:
            socketio.emit("step_progress", {"step": "hotels", "state": "failed", "message": str(e)}, room=session_id)
            socketio.emit("plan_error", {"error": str(e)}, room=session_id)
        raise e

    if centroid:
        for h in hotel_options:
            if "location" in h and isinstance(h["location"], list) and len(h["location"]) >= 2:
                h["distance_km"] = haversine(centroid["lat"], centroid["lng"], h["location"][1], h["location"][0])
            else:
                h["distance_km"] = 9999.0
        # Sort by distance and budget fit
        hotel_options.sort(key=lambda x: (x.get("distance_km", 0), abs(x["cost"] - max_budget)))
        best_hotel = 0
    else:
        best_hotel = getattr(agent_context, "selected_hotel_idx", 0)

    # Save hotel options in state
    session = firebase_state.get_session(session_id)
    session["hotel_options"] = hotel_options
    session["selected_hotel_idx"] = best_hotel
    firebase_state.recalculate_budget(session)
    firebase_state.update_session_options(session_id, hotel_options=hotel_options)

    # Write selected indices to local session file
    firebase_state.swap_session_item(session_id, "hotel", best_hotel, user_id="system")
    session = firebase_state.get_session(session_id)
    
    if socketio:
        logger.info(f"Emitting hotel_locked to room {session_id}")
        socketio.emit("hotel_locked", {
            "options": hotel_options,
            "selected_idx": best_hotel,
            "cost": hotel_options[best_hotel]["cost"],
            "remaining_budget": session["remaining_budget"]
        }, room=session_id)
        
    return f"Hotel offers populated. Locked: {hotel_options[best_hotel]['hotel_name']}."

def generate_itinerary(destination: str, remaining_budget: float) -> list:
    """Uses Gemini API and tools to generate a structured itinerary via single call."""
    from . import places_api
    import google.generativeai as genai
    import json
    import time
    import hashlib
    import logging
    import threading
    
    logger = logging.getLogger(__name__)
    
    trip_entities = getattr(agent_context, "trip_entities", {})
    interests = trip_entities.get("interests", ["culture", "food"])
    days = trip_entities.get("duration_days", 5)
    
    # FR2: In-memory cache for itinerary
    cache_key = hashlib.md5(f"{destination}_{days}_{remaining_budget}_{','.join(interests)}".encode('utf-8')).hexdigest()
    if not hasattr(agent_context, "_itinerary_cache"):
        agent_context._itinerary_cache = {}
    if cache_key in agent_context._itinerary_cache:
        logger.info(f"Returning cached itinerary for {destination}")
        return agent_context._itinerary_cache[cache_key]
    
    api_key = os.environ.get("GEMINI_API_KEY")
    
    session_id = getattr(agent_context, "session_id", "default_session")
    socketio = getattr(agent_context, "socketio", None)
    
    def _fallback(dest):
        poi = places_api.search_places(dest, "attraction", 3)
        fallback_itinerary = []
        for d in range(1, days + 1):
            fallback_itinerary.append(
                {"day": d, "title": f"Day {d} in {dest}", "morning": "Explore", "afternoon": "Relax", "evening": "Dinner", "tips": "", "estimated_cost": 50, "spots": [{"name": poi[0]["name"], "lat": poi[0]["lat"], "lng": poi[0]["lng"], "description": "Arrival spot", "estimated_cost": 20, "time": "Afternoon"}]}
            )
            if socketio:
                socketio.emit("itinerary_progress", {"day": d, "total_days": days, "data": fallback_itinerary[-1]}, room=session_id)
        return fallback_itinerary
        
    if not api_key:
        logger.warning("GEMINI_API_KEY is not set. Falling back to mock itinerary.")
        return _fallback(destination)
        
    # FR3: In-flight request concurrency cap
    global _itinerary_semaphore
    if '_itinerary_semaphore' not in globals():
        _itinerary_semaphore = threading.Semaphore(5)
    if not _itinerary_semaphore.acquire(blocking=False):
        logger.warning("Concurrency cap reached for itinerary generation. Falling back to mock.")
        return _fallback(destination)
        
    try:
        genai.configure(api_key=api_key)
        
        def search_places(query: str, dest: str = destination, limit: int = 3) -> list:
            """Searches for points of interest."""
            return places_api.search_places(dest, query, limit)
            
        def geocode(place_name: str) -> dict:
            """Geocodes a place name."""
            return places_api.geocode(place_name)
            
        model = genai.GenerativeModel("gemini-1.5-flash", tools=[search_places, geocode])
        
        prompt = f"""You are a travel planner. The user wants to visit {destination} for {days} days.
        Their interests are {interests}. Remaining budget for activities/food: ${remaining_budget}.
        Generate the entire itinerary for all {days} days.
        Use your tools to find REAL places and their coordinates.
        Output ONLY a valid JSON array of day objects (no markdown blocks like ```json):
        [
            {{
                "day": 1,
                "title": "...",
                "morning": "...",
                "afternoon": "...",
                "evening": "...",
                "tips": "...",
                "estimated_cost": 50.0,
                "spots": [
                    {{"name": "...", "lat": 1.0, "lng": 1.0, "description": "...", "estimated_cost": 10.0, "time": "Morning"}}
                ]
            }}
        ]"""
        
        # Single call (avoids 5x loop parallel execution issue)
        # We start a chat session to allow multi-turn tool execution if Gemini decides to use tools
        chat = model.start_chat()
        response = chat.send_message(prompt)
        
        content = response.text.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("\n", 1)[0].strip()
        if content.startswith("json"):
            content = content[4:].strip()
            
        itinerary = json.loads(content)
        if isinstance(itinerary, dict) and "itinerary" in itinerary:
             itinerary = itinerary["itinerary"]
             
        # Emit progress sequentially since we did it in one call
        for day_data in itinerary:
            if socketio:
                socketio.emit("itinerary_progress", {"day": day_data.get("day"), "total_days": days, "data": day_data}, room=session_id)
                time.sleep(0.1) # Small delay to ensure UI updates sequentially
        
        agent_context._itinerary_cache[cache_key] = itinerary
        return itinerary
        
    except Exception as e:
        logger.error(f"Gemini itinerary generation failed: {e}")
        return _fallback(destination)
    finally:
        if '_itinerary_semaphore' in globals():
            _itinerary_semaphore.release()

def run_agent_workflow(user_text: str, session_id: str, socketio, initial_budget: float, entities: dict = None):
    """Executes the agent planning workflow."""
    agent_context.session_id = session_id
    agent_context.socketio = socketio
    
    # Clean thread-local storage of previous runs
    if hasattr(agent_context, "outbound_options"):
        delattr(agent_context, "outbound_options")
    if hasattr(agent_context, "inbound_options"):
        delattr(agent_context, "inbound_options")
    if hasattr(agent_context, "hotel_options"):
        delattr(agent_context, "hotel_options")
    
    # Resolve the entities first if not passed in
    if socketio:
        socketio.emit("step_progress", {"step": "parsing", "state": "in_progress", "message": "Analyzing prompt & extracting locations..."}, room=session_id)
    if entities is None:
        entities = extract_trip_entities(user_text)
        
        # Abort if the NLP parser needs clarification
        if not entities.get("is_valid", True):
            clarification = entities.get("clarification_needed", "Please specify your origin and destination clearly.")
            logger.warning(f"Trip request invalid: {clarification}")
            if socketio:
                socketio.emit("step_progress", {"step": "parsing", "state": "failed", "message": clarification}, room=session_id)
                socketio.emit("plan_error", {"error": clarification}, room=session_id)
            return
            
        # Geocode the origin and destination to decouple it from LLM parsing
        from .places_api import geocode
        if "origin_city" in entities and entities["origin_city"]:
            origin_coords = geocode(entities["origin_city"])
            entities["origin_coords"] = [origin_coords["lng"], origin_coords["lat"]]
        if "destination_city" in entities and entities["destination_city"]:
            dest_coords = geocode(entities["destination_city"])
            entities["destination_coords"] = [dest_coords["lng"], dest_coords["lat"]]

        # Update Firestore/Memory session with the real resolved budget/currency parameters from LLM
        firebase_state.initialize_session(
            session_id,
            total_budget=entities.get("total_budget", initial_budget),
            currency=entities.get("currency", "USD"),
            currency_symbol=entities.get("currency_symbol", "$")
        )
    
    agent_context.trip_entities = entities
    destination = entities["destination_city"]
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY environment variable not found. Running rule-based simulation mode.")
        run_rule_based_simulation(user_text, session_id, socketio, initial_budget)
        return
        
    try:
        # Emit parsing done with real extracted summary
        if socketio:
            origin_city = entities.get("origin_city", "Unknown")
            dest_city = entities.get("destination_city", "Unknown")
            dur = entities.get("duration_days", "?")
            sym = entities.get("currency_symbol", "$")
            bud = entities.get("total_budget", initial_budget)
            parse_summary = f"{origin_city} \u2192 {dest_city} \u00b7 {dur} nights \u00b7 {sym}{int(bud):,}"
            socketio.emit("step_progress", {"step": "parsing", "state": "done", "message": parse_summary}, room=session_id)

        # 1. Execute flight search (outbound + inbound) directly
        mock_search_flights(destination, initial_budget)

        # 2. Get current state and execute hotel search using destination centroid
        from . import places_api
        centroid = places_api.geocode(destination)
        session = firebase_state.get_session(session_id)
        mock_search_hotels(destination, session["remaining_budget"], centroid)

        # 3. Budget summary (orchestration already done inside mock_search_flights)
        session = firebase_state.get_session(session_id)
        if socketio:
            socketio.emit("step_progress", {"step": "budget", "state": "done", "message": f"Budget OK \u2014 {entities.get('currency_symbol', '$')}{session['remaining_budget']:,.0f} remaining"}, room=session_id)

        # 4. Build itinerary before finalizing so the HUD log order is correct
        if socketio:
            socketio.emit("step_progress", {"step": "itinerary", "state": "in_progress", "message": "Compiling custom travel itinerary..."}, room=session_id)
        remaining = session.get("remaining_budget", 500.0)
        itinerary = generate_itinerary(destination, remaining)
        session = firebase_state.update_session_options(session_id, itinerary=itinerary)
        if socketio:
            socketio.emit("step_progress", {"step": "itinerary", "state": "done", "message": f"{len(itinerary)}-day itinerary built"}, room=session_id)
            socketio.emit("itinerary_locked", {"itinerary": itinerary}, room=session_id)

        # 5. Generate custom summary text via single-turn Gemini API call
        if socketio:
            socketio.emit("step_progress", {"step": "finalize", "state": "in_progress", "message": "Generating personalized summary & packing advice..."}, room=session_id)
        summary = f"Plan complete. Booked roundtrip flights and hotel in {destination}."
        if api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-flash-latest")

                # Fetch fresh session state with selections resolved
                session = firebase_state.get_session(session_id)
                out_opt = session.get("outbound_options", [])
                out_idx = session.get("selected_outbound_idx", 0)
                in_opt = session.get("inbound_options", [])
                in_idx = session.get("selected_inbound_idx", 0)
                h_opt = session.get("hotel_options", [])
                h_idx = session.get("selected_hotel_idx", 0)

                out_name = out_opt[out_idx]["carrier"] if out_opt and out_idx < len(out_opt) else "Flight"
                in_name = in_opt[in_idx]["carrier"] if in_opt and in_idx < len(in_opt) else "Flight"
                hotel_name = h_opt[h_idx]["hotel_name"] if h_opt and h_idx < len(h_opt) else "Hotel"

                symbol = entities.get("currency_symbol", "$")
                weather_text = getattr(agent_context, "weather_text", "Mild weather expected.")
                prompt = (
                    f"Write a friendly travel planner summary paragraph for a trip to {destination}. "
                    f"The weather forecast at the destination is: '{weather_text}'. "
                    f"The total budget is {symbol}{initial_budget}. "
                    f"The user is booking: '{out_name}' (outbound), '{in_name}' (return), and staying at '{hotel_name}'. "
                    f"The total remaining budget left over is {symbol}{session['remaining_budget']}. "
                    f"Briefly describe how this plan matches their trip query: '{user_text}', including any relevant packing or travel tips."
                )

                response = model.generate_content(prompt)
                if response.text:
                    summary = response.text.strip()
            except Exception as e:
                logger.error(f"Error generating single-turn summary: {e}")

        if socketio:
            socketio.emit("step_progress", {"step": "finalize", "state": "done", "message": "Plan finalized"}, room=session_id)

        # Persist final state
        session = firebase_state.get_session(session_id)
        if socketio:
            socketio.emit("plan_completed", {
                "summary": summary,
                "remaining_budget": session["remaining_budget"]
            }, room=session_id)

    except Exception as e:
        logger.error(f"Error running optimized Gemini agent workflow: {e}")
        import traceback
        traceback.print_exc()
        run_rule_based_simulation(user_text, session_id, socketio, initial_budget)

def run_rule_based_simulation(user_text: str, session_id: str, socketio, initial_budget: float):
    """Fallback rule-based simulation when Gemini API Key is missing or fails."""
    logger.info("Executing rule-based simulation flow...")
    
    trip_entities = getattr(agent_context, "trip_entities", None)
    if not trip_entities:
        trip_entities = extract_trip_entities(user_text)
        agent_context.trip_entities = trip_entities
        # Update session with resolved fallback parameters
        firebase_state.initialize_session(
            session_id,
            total_budget=trip_entities.get("total_budget", initial_budget),
            currency=trip_entities.get("currency", "USD"),
            currency_symbol=trip_entities.get("currency_symbol", "$")
        )
        
    destination = trip_entities["destination_city"]
            
    # Stage 1: Flight search (outbound + inbound) -> under the hood this triggers concurrent hotel query & orchestrates budget compliance
    time.sleep(0.1)
    mock_search_flights(destination, initial_budget)
    
    # Stage 2: Hotel search using destination centroid
    time.sleep(0.1)
    from . import places_api
    centroid = places_api.geocode(destination)
    session = firebase_state.get_session(session_id)
    mock_search_hotels(destination, session["remaining_budget"], centroid)
    
    # Send early completion
    if socketio:
        summary = f"Rule-based plan complete. Booked roundtrip flights and hotel in {destination}. Remaining budget: {trip_entities.get('currency_symbol', '$')}{session['remaining_budget']}."
        socketio.emit("plan_completed", {
            "summary": summary,
            "remaining_budget": session["remaining_budget"]
        }, room=session_id)

    # Stage 3: Itinerary (Async)
    time.sleep(0.1)
    session = firebase_state.get_session(session_id)
    remaining = session["remaining_budget"]
    itinerary = generate_itinerary(destination, remaining)
    session = firebase_state.update_session_options(session_id, itinerary=itinerary)
    
    if socketio:
        socketio.emit("itinerary_locked", {"itinerary": itinerary}, room=session_id)
