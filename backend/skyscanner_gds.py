"""
skyscanner_gds.py — GDS Flight & Hotel search layer.

Priority:
  1. Duffel API (real airline fares — requires duffel_live_... key for real prices)
  2. TripAdvisor via RapidAPI (real hotel prices)

NOTE: The Duffel API key type matters critically:
  - duffel_test_... keys return SYNTHETIC/FAKE prices (sandbox mode).
  - duffel_live_... keys return REAL airline inventory and prices.
  If prices appear unrealistically low, check that a duffel_live_... key is configured.

All responses are cached in Redis (or in-memory fallback) for 4 minutes (below
typical Duffel offer expiry) to avoid showing stale/expired prices.
"""
import os
import re
import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Optional

import requests

from . import redis_cache

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Exchange rates (relative to USD baseline)
# Hard-coded as a reasonable approximation; Duffel returns offers in their
# own currency so we convert to the user's requested currency here.
# ---------------------------------------------------------------------------
EXCHANGE_RATES = {
    "USD": 1.0,
    "IDR": 15500.0,
    "JPY": 150.0,
    "CNY": 7.2,
    "EUR": 0.92,
    "GBP": 0.79,
    "SGD": 1.34,
    "AUD": 1.50,
}

# Warn loudly on startup if a test key is detected
_duffel_key = os.environ.get("DUFFEL_API_KEY", "")
if _duffel_key.startswith("duffel_test_"):
    logger.warning(
        "[Duffel] ⚠️  DUFFEL_API_KEY is a SANDBOX/TEST key (duffel_test_...). "
        "All flight prices returned will be SYNTHETIC and will NOT match real market rates. "
        "Set a duffel_live_... key to get real airline fares."
    )
elif _duffel_key.startswith("duffel_live_"):
    logger.info("[Duffel] ✅ Live API key detected — real airline fares will be returned.")


def _convert_to_user_currency(amount: float, offer_currency: str, user_currency: str) -> float:
    """Convert amount from Duffel's offer currency to the user's requested currency."""
    if offer_currency == user_currency:
        return amount
    rate_from = EXCHANGE_RATES.get(offer_currency.upper(), 1.0)
    rate_to = EXCHANGE_RATES.get(user_currency.upper(), 1.0)
    # Convert offer_currency → USD → user_currency
    usd_amount = amount / rate_from
    return round(usd_amount * rate_to, 2)

# ---------------------------------------------------------------------------
# Amadeus OAuth2 client
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Wikipedia Action API: Points of Interest (POI) Search
# ---------------------------------------------------------------------------
def _wikipedia_search_pois(latitude: float, longitude: float) -> Optional[list]:
    """Call Wikipedia Action API geosearch. Returns None on failure."""
    cache_key = f"pois:wikipedia:{latitude:.4f}:{longitude:.4f}"
    cached = redis_cache.get(cache_key)
    if cached:
        logger.info(f"[Cache HIT] Wikipedia POIs near {latitude}, {longitude}")
        return cached

    try:
        url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "list": "geosearch",
            "gscoord": f"{latitude}|{longitude}",
            "gsradius": 5000,  # 5 km radius
            "gslimit": 10,
            "format": "json"
        }
        headers = {
            "User-Agent": "TravelAgenticEngine/1.0 (contact@example.com)"
        }
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        
        pages = data.get("query", {}).get("geosearch", [])
        if not pages:
            return None

        results = []
        for page in pages:
            title = page.get("title")
            if not title:
                continue
            category = "SIGHTS"
            results.append({
                "name": title,
                "category": category,
                "latitude": page["lat"],
                "longitude": page["lon"],
            })

        redis_cache.set(cache_key, results, ttl=600)
        logger.info(f"[Wikipedia] Live POI results cached for {latitude}, {longitude}")
        return results
    except Exception as e:
        logger.error(f"[Wikipedia] POI search error: {e}")
        return None

# ---------------------------------------------------------------------------
# RapidAPI Flight & Hotel Resolvers
# ---------------------------------------------------------------------------
def _resolve_airport(query: str, api_key: str) -> Optional[tuple[str, str]]:
    """Helper to resolve IATA code to (skyId, entityId) using searchAirport."""
    try:
        url = "https://sky-scrapper.p.rapidapi.com/api/v1/flights/searchAirport"
        headers = {
            "x-rapidapi-key": api_key,
            "x-rapidapi-host": "sky-scrapper.p.rapidapi.com"
        }
        params = {
            "query": query,
            "locale": "en-US"
        }
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        if data:
            flight_params = data[0].get("navigation", {}).get("relevantFlightParams", {})
            sky_id = flight_params.get("skyId")
            entity_id = flight_params.get("entityId")
            if sky_id and entity_id:
                return sky_id, entity_id
    except Exception as e:
        logger.error(f"[RapidAPI] Airport lookup error for {query}: {e}")
    return None


TRIPADVISOR_CITY_MAP = {
    "TOKYO": "298184",
    "KYOTO": "298564",
    "OSAKA": "298566",
    "LONDON": "186338",
    "PARIS": "187147",
    "NEW YORK": "60763",
    "JAKARTA": "294229",
    "BALI": "294226",
    "SINGAPORE": "294265",
    "BANGKOK": "293916",
    "SEOUL": "294197",
    "SYDNEY": "255060",
    "ROME": "187791",
    "BARCELONA": "187497",
    "DUBAI": "295424",
    "SAN FRANCISCO": "60713",
    "HONOLULU": "60982",
    "HAWAII": "60607",
    "KUALA LUMPUR": "298570",
    "HONG KONG": "294217",
    "SHANGHAI": "308272",
    "TAIPEI": "293913",
    "ISTANBUL": "293974",
    "AMSTERDAM": "188590",
    "BERLIN": "187323",
    "MUMBAI": "304554",
    "DELHI": "304551",
    "CAIRO": "294201",
    "MANILA": "298573",
}

def _resolve_hotels_location(query: str, api_key: str) -> Optional[str]:
    """Resolves city name to TripAdvisor geoId."""
    q_clean = query.strip().upper()
    # Check pre-mapped list first to fast-path common search queries
    for city, geo_id in TRIPADVISOR_CITY_MAP.items():
        if city in q_clean or q_clean in city:
            return geo_id
            
    # Try live query resolver
    try:
        url = "https://tripadvisor16.p.rapidapi.com/api/v1/hotels/searchLocation"
        headers = {
            "x-rapidapi-key": api_key,
            "x-rapidapi-host": "tripadvisor16.p.rapidapi.com"
        }
        params = {"query": query}
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        if data:
            return str(data[0].get("geoId"))
    except Exception as e:
        logger.error(f"[RapidAPI] Hotel location lookup error for {query}: {e}")
    return None


# ---------------------------------------------------------------------------
# Duffel API Live: Flight Search
# ---------------------------------------------------------------------------
def _duffel_search_flights(
    origin: str,
    destination: str,
    date: str,
    user_currency: str,
    max_results: int = 5,
) -> Optional[list]:
    """Call Duffel API for flights. Returns None on failure.
    
    Captures: offer id, total_amount, total_currency, expires_at for full traceability.
    Converts the Duffel offer currency to the user's requested currency.
    Cache TTL is 4 minutes — below typical Duffel offer expiry — so stale offers
    are not shown as bookable.
    """
    api_key = os.environ.get("DUFFEL_API_KEY", "").strip().strip("'\"")
    if not api_key:
        logger.warning("[Duffel] DUFFEL_API_KEY is missing.")
        return None

    # TTL = 240s (4 min) — Duffel offers typically expire in 10–30 min but
    # we keep it short to avoid surfacing stale prices after cache hits.
    CACHE_TTL = 240
    cache_key = redis_cache.make_flight_key(origin, destination, date, user_currency, "duffel")
    cached = redis_cache.get(cache_key)
    if cached:
        logger.info(f"[Cache HIT] Duffel flights {origin}→{destination} {date}")
        return cached

    try:
        url = "https://api.duffel.com/air/offer_requests"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Duffel-Version": "v2",
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip"
        }
        
        payload = {
            "data": {
                "slices": [
                    {
                        "origin": origin,
                        "destination": destination,
                        "departure_date": date
                    }
                ],
                "passengers": [{"type": "adult"}],
                "cabin_class": "economy"
            }
        }
        
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        resp.raise_for_status()
        data = resp.json().get("data", {})
        offers = data.get("offers", [])
        
        if not offers:
            logger.warning(f"[Duffel] No offers returned for {origin}→{destination} on {date}")
            return None

        # Sort offers by total_amount ascending
        offers.sort(key=lambda x: float(x.get("total_amount", 0.0)))
        
        results = []
        for offer in offers[:max_results]:
            # --- DIAGNOSTIC LOGGING: all price-relevant fields ---
            offer_id = offer.get("id", "unknown")
            raw_amount = offer.get("total_amount", "0.0")
            offer_currency = offer.get("total_currency", "USD")
            expires_at = offer.get("expires_at", "unknown")
            logger.info(
                f"[Duffel] Offer diagnostic — id={offer_id}, "
                f"total_amount={raw_amount} {offer_currency}, "
                f"expires_at={expires_at}, route={origin}→{destination}"
            )

            raw_cost = float(raw_amount)
            if raw_cost == 0.0:
                continue

            # Convert from Duffel offer currency to user-requested currency
            cost = _convert_to_user_currency(raw_cost, offer_currency, user_currency)

            slices = offer.get("slices", [])
            carrier = f"Airline flight {origin}→{destination}"
            stop_count = 0
            duration_min = 0
            
            if slices:
                first_slice = slices[0]
                duration_str = first_slice.get("duration", "PT0M")
                h_match = re.search(r'(\d+)H', duration_str)
                m_match = re.search(r'(\d+)M', duration_str)
                if h_match: duration_min += int(h_match.group(1)) * 60
                if m_match: duration_min += int(m_match.group(1))
                
                segments = first_slice.get("segments", [])
                stop_count = max(0, len(segments) - 1)
                
                if segments:
                    operating = segments[0].get("operating_carrier") or {}
                    marketing = segments[0].get("marketing_carrier") or {}
                    carrier_name = operating.get("name") or marketing.get("name", "Airline")
                    stop_label = "Direct" if stop_count == 0 else f"{stop_count} Stop{'s' if stop_count > 1 else ''}"
                    duration_h = duration_min // 60
                    duration_m = duration_min % 60
                    carrier = f"{carrier_name} ({stop_label}, {duration_h}h{duration_m:02d}m)"
                    
            results.append({
                "cost": cost,
                "raw_cost": raw_cost,
                "offer_currency": offer_currency,
                "offer_id": offer_id,
                "expires_at": expires_at,
                "carrier": carrier,
                "cabin": "ECONOMY",
                "stops": stop_count,
                "duration_minutes": duration_min,
            })

        redis_cache.set(cache_key, results, ttl=CACHE_TTL)
        logger.info(f"[Duffel] {len(results)} flight offers cached for {origin}→{destination} (TTL={CACHE_TTL}s)")
        return results
    except Exception as e:
        logger.error(f"[Duffel] Flight search error: {e}")
        return None

# ---------------------------------------------------------------------------
# RapidAPI Live: Hotel Search (Hotels.com)
# ---------------------------------------------------------------------------
def _rapidapi_search_hotels(destination: str, currency: str) -> Optional[list]:
    """Call Hotels.com API via RapidAPI. Returns None on failure."""
    api_key = os.environ.get("RAPIDAPI_KEY", "").strip().strip("'\"")
    api_host = os.environ.get("RAPIDAPI_HOST", "hotels-com-provider.p.rapidapi.com").strip().strip("'\"")
    if not api_key:
        logger.warning("[Hotels.com] RAPIDAPI_KEY is missing.")
        return None

def _rapidapi_search_hotels(
    destination: str,
    currency: str = "USD",
    checkin: Optional[str] = None,
    checkout: Optional[str] = None,
    num_nights: int = 5,
) -> list:
    """Live hotel search using Tripadvisor16 on RapidAPI.
    
    Args:
        checkin:   ISO date string for check-in (e.g. '2025-08-14'). Defaults to now+30d.
        checkout:  ISO date string for check-out. Defaults to checkin + num_nights.
        num_nights: Number of nights to stay; used to compute total_cost from per-night rate.
    """
    # Resolve dates — use actual trip dates if supplied, else fall back to +30 days
    if not checkin:
        checkin = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    if not checkout:
        checkin_dt = datetime.strptime(checkin, "%Y-%m-%d")
        checkout = (checkin_dt + timedelta(days=num_nights)).strftime("%Y-%m-%d")

    cache_key = redis_cache.make_flight_key(destination, "HOTELS", checkin, currency, "tripadvisor")
    cached = redis_cache.get(cache_key)
    if cached:
        logger.info(f"[Cache HIT] RapidAPI Tripadvisor for {destination} ({checkin}→{checkout})")
        return cached

    try:
        api_key = os.environ.get("RAPIDAPI_KEY")
        if not api_key:
            return None

        # GeoId map for Tripadvisor16 (city → locationId used for deep-linking too)
        GEO_MAP = {
            "tokyo": ("298184", "Asakusa"),
            "kyoto": ("298564", "Kyoto"),
            "osaka": ("298566", "Osaka"),
            "london": ("186338", "London"),
            "paris": ("187147", "Paris"),
            "new york": ("60763", "New-York-City"),
            "dubai": ("295424", "Dubai"),
            "singapore": ("294265", "Singapore"),
            "seoul": ("294197", "Seoul"),
            "bali": ("297628", "Bali"),
            "jakarta": ("294229", "Jakarta"),
            "bangkok": ("293916", "Bangkok"),
            "sydney": ("255060", "Sydney"),
            "rome": ("187791", "Rome"),
            "barcelona": ("187497", "Barcelona"),
            "san francisco": ("60713", "San-Francisco"),
            "amsterdam": ("188590", "Amsterdam"),
            "berlin": ("187323", "Berlin"),
            "kuala lumpur": ("298570", "Kuala-Lumpur"),
            "hong kong": ("294217", "Hong-Kong"),
            "istanbul": ("293974", "Istanbul"),
        }
        dest_lower = destination.lower()
        geo_id, geo_slug = next(
            ((gid, slug) for city, (gid, slug) in GEO_MAP.items() if city in dest_lower or dest_lower in city),
            ("298184", destination.replace(" ", "-"))  # fallback: Tokyo geoId
        )
        
        url = "https://tripadvisor16.p.rapidapi.com/api/v1/hotels/searchHotels"
        headers = {
            "x-rapidapi-key": api_key,
            "x-rapidapi-host": "tripadvisor16.p.rapidapi.com"
        }
        params = {
            "geoId": geo_id,
            "checkIn": checkin,
            "checkOut": checkout,
            "pageNumber": "1",
            "currencyCode": currency
        }
        
        logger.info(f"[Tripadvisor] Searching hotels in {destination} (geoId={geo_id}), {checkin}→{checkout} ({num_nights} nights), currency={currency}")
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        
        data = resp.json().get("data", {}).get("data", [])
        if not data:
            logger.warning(f"[Tripadvisor] No hotel results for {destination} (geoId={geo_id})")
            return None
            
        results = []
        for prop in data[:5]:
            hotel_name = prop.get("title", "Hotel")
            ta_location_id = str(prop.get("locationId", ""))

            # priceForDisplay is the nightly rate for the searched dates (not a teaser)
            price_str = prop.get("priceForDisplay") or prop.get("rawRanking", "")
            cleaned_price = re.sub(r"[^\d.]", "", str(price_str))
            try:
                per_night = float(cleaned_price) if cleaned_price else 0.0
            except ValueError:
                per_night = 0.0

            if per_night == 0.0:
                logger.warning(f"[Tripadvisor] No parseable price for '{hotel_name}' — skipping.")
                continue

            total_cost = round(per_night * num_nights, 2)

            # --- DIAGNOSTIC LOGGING ---
            logger.info(
                f"[Tripadvisor] Hotel diagnostic — name='{hotel_name}', "
                f"locationId={ta_location_id}, per_night={per_night} {currency}, "
                f"num_nights={num_nights}, total_cost={total_cost}, "
                f"checkin={checkin}, checkout={checkout}"
            )
                
            rating = prop.get("bubbleRating", {}).get("rating", 0.0)
            
            thumbnail = ""
            photos = prop.get("cardPhotos", [])
            if photos:
                sizes = photos[0].get("sizes", {})
                if sizes.get("urlTemplate"):
                    thumbnail = sizes["urlTemplate"].replace("{width}", "800").replace("{height}", "600")

            booking_link = _hotel_link(hotel_name, destination, currency, ta_location_id, checkin, checkout)
            
            results.append({
                "hotel_name": hotel_name,
                "cost": total_cost,
                "per_night": per_night,
                "num_nights": num_nights,
                "rating": rating,
                "thumbnail": thumbnail,
                "booking_link": booking_link,
                "location_id": ta_location_id,
            })
            
            if len(results) >= 3:
                break

        if not results:
            logger.warning(f"[Tripadvisor] All returned hotels had no parseable price for {destination}.")
            return None

        redis_cache.set(cache_key, results, ttl=600)
        logger.info(f"[Tripadvisor] {len(results)} hotels cached for {destination} ({checkin}→{checkout})")
        return results
    except Exception as e:
        logger.error(f"[Tripadvisor] Hotel search error: {e}")
        return None

# ---------------------------------------------------------------------------
# Booking deep-link builders
# ---------------------------------------------------------------------------
def _booking_link(origin: str, destination: str, date: str, currency: str, cabin: str = "y", carrier: str = "") -> str:
    """Returns a real, valid flight search URL (Google Flights deep query or Traveloka search)."""
    if currency == "IDR":
        class_code = "BUSINESS" if cabin == "c" else "ECONOMY"
        return f"https://www.traveloka.com/en-id/flight/search?ap={origin}.{destination}&dt={date}.NA&ps=1.0.0&sc={class_code}"
    
    # Google Flights query structure: never 404s, parses queries dynamically
    class_label = "business" if cabin == "c" else "economy"
    clean_carrier = carrier.split("(")[0].strip() if carrier else ""
    carrier_query = f"{clean_carrier} " if clean_carrier else ""
    query = f"{carrier_query}flights from {origin} to {destination} on {date} {class_label}"
    import urllib.parse
    q_encoded = urllib.parse.quote(query)
    return f"https://www.google.com/travel/flights?q={q_encoded}"



def _hotel_link(
    hotel_name: str,
    city_name: str,
    currency: str,
    location_id: str = "",
    checkin: str = "",
    checkout: str = "",
) -> str:
    """Returns a Hotels.com deep-link for the specific property and dates.
    
    If a TripAdvisor locationId is available, links directly to the Hotels.com
    property page with the correct dates. Falls back to a Hotels.com search URL.
    """
    import urllib.parse
    # Hotels.com search deep-link — includes hotel name, city, and dates
    encoded_name = urllib.parse.quote(hotel_name)
    encoded_city = urllib.parse.quote(city_name)
    base = "https://www.hotels.com/search.do"
    params = f"?q-destination={encoded_city}&q-localised-check-in={checkin}&q-localised-check-out={checkout}&q-rooms=1&q-room-0-adults=1"
    # Append hotel name as a text filter so the specific property appears first
    params += f"&q-text={encoded_name}"
    if currency and currency != "USD":
        params += f"&pos=HCOM_{currency.upper()}"
    return f"{base}{params}"

# ---------------------------------------------------------------------------
# Public entry points (called from gemini_agent.py)
# ---------------------------------------------------------------------------
def mock_gds_search_flights(
    origin: str,
    destination: str,
    currency: str,
    direction: str,
    total_budget: float = 1000.0,
    departure_date: Optional[str] = None,
) -> list:
    """Search flights via Duffel API using real airline inventory.
    
    Args:
        departure_date: ISO date string (YYYY-MM-DD) for the actual trip date.
                        If not provided, defaults to now+30d (outbound) / now+37d (inbound).
    """
    logger.info(f"[GDS] {direction} flights {origin}→{destination} ({currency})")

    # Use provided trip dates if available, else fall back to +30/+37 days
    if departure_date:
        date_str = departure_date
    else:
        future_out = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        future_in = (datetime.now() + timedelta(days=37)).strftime("%Y-%m-%d")
        date_str = future_out if direction == "outbound" else future_in
    prefix = "out" if direction == "outbound" else "in"

    # --- Live Duffel Search ---
    live_results = _duffel_search_flights(origin, destination, date_str, currency)
    if live_results and len(live_results) > 0:
        logger.info(f"[Duffel] Returning {len(live_results)} live offers for {origin}→{destination} on {date_str}")
        options = []
        for i, r in enumerate(live_results):
            cabin_code = "c" if r.get("cabin", "ECONOMY") in ("BUSINESS", "FIRST") else "y"
            checkout_url = _booking_link(origin, destination, date_str, currency, cabin_code, r.get("carrier", ""))
            options.append({
                "id": f"{prefix}-live-{i+1}",
                "carrier": r["carrier"],
                "cost": r["cost"],
                "offer_currency": r.get("offer_currency", currency),
                "offer_id": r.get("offer_id", ""),
                "expires_at": r.get("expires_at", ""),
                "skyscanner_link": checkout_url,
                "source": "duffel_live",
            })
        return options
        
    logger.warning(f"[Duffel] No live flight results for {origin}→{destination}")
    raise Exception(f"No live flight results found for {origin}→{destination} via Duffel. Check API key or availability.")


def mock_gds_search_hotels(
    destination: str,
    currency: str,
    total_budget: float = 1000.0,
    destination_iata: str = "",
    checkin: Optional[str] = None,
    checkout: Optional[str] = None,
    num_nights: int = 5,
) -> list:
    """Search hotels via TripAdvisor/RapidAPI using real prices for actual trip dates.
    
    Args:
        checkin:    Actual trip check-in date (ISO, YYYY-MM-DD).
        checkout:   Actual trip check-out date (ISO, YYYY-MM-DD).
        num_nights: Number of nights (derived from checkin/checkout if both provided).
    """
    logger.info(f"[GDS] Hotels in {destination} ({currency}), {checkin}→{checkout} ({num_nights} nights)")

    # If both dates are given, recompute num_nights to ensure consistency
    if checkin and checkout:
        try:
            ci = datetime.strptime(checkin, "%Y-%m-%d")
            co = datetime.strptime(checkout, "%Y-%m-%d")
            num_nights = max(1, (co - ci).days)
        except ValueError:
            pass

    # --- Live TripAdvisor Search ---
    live_results = _rapidapi_search_hotels(destination, currency, checkin, checkout, num_nights)
    if live_results and len(live_results) > 0:
        logger.info(f"[Hotels.com] Returning {len(live_results)} live hotels for {destination}")
        options = []
        for i, r in enumerate(live_results):
            options.append({
                "id": f"hotel-live-{i+1}",
                "hotel_name": r["hotel_name"],
                "cost": r["cost"],
                "per_night": r.get("per_night", 0.0),
                "num_nights": r.get("num_nights", num_nights),
                "booking_link": r.get("booking_link", _hotel_link(r["hotel_name"], destination, currency, "", checkin or "", checkout or "")),
                "rating": r.get("rating", 0.0),
                "thumbnail": r.get("thumbnail", ""),
                "source": "tripadvisor_live",
            })
        return options

    logger.warning(f"[Hotels.com] No live hotel results for {destination}")
    raise Exception(f"No live hotel results found for {destination} via TripAdvisor/RapidAPI. Check API key or availability.")

def mock_gds_search_pois(latitude: float, longitude: float) -> list:
    """Mock POI search."""
    return [
        {"name": "Local Museum", "category": "museum"},
        {"name": "City Park", "category": "park"},
        {"name": "Central Plaza", "category": "landmark"},
    ]
