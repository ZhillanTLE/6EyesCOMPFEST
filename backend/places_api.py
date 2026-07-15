import os
import logging
import requests

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

def geocode(place_name: str) -> dict:
    """Geocodes a place name into latitude and longitude."""
    api_key = os.environ.get("PLACES_API_KEY")
    if api_key:
        try:
            url = f"https://maps.googleapis.com/maps/api/geocode/json?address={requests.utils.quote(place_name)}&key={api_key}"
            response = requests.get(url, timeout=5)
            data = response.json()
            if data.get("status") == "OK" and len(data.get("results", [])) > 0:
                location = data["results"][0]["geometry"]["location"]
                return {"lat": location["lat"], "lng": location["lng"]}
        except Exception as e:
            logger.error(f"Geocoding error for {place_name}: {e}")
            
    # Mock fallback
    logger.warning(f"Using mock geocoding for {place_name}")
    place_lower = place_name.lower()
    for key, coords in DESTINATIONS.items():
        if key in place_lower:
            return {"lat": coords[1], "lng": coords[0]}
            
    # Default to Tokyo if no match
    import random
    base = DESTINATIONS["tokyo"]
    return {
        "lat": base[1] + random.uniform(-0.05, 0.05),
        "lng": base[0] + random.uniform(-0.05, 0.05)
    }

def search_places(destination: str, query: str, limit: int = 5) -> list:
    """Searches for points of interest based on a query in a specific destination."""
    api_key = os.environ.get("PLACES_API_KEY")
    if api_key:
        try:
            center = geocode(destination)
            if center:
                url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={requests.utils.quote(query + ' in ' + destination)}&location={center['lat']},{center['lng']}&radius=5000&key={api_key}"
                response = requests.get(url, timeout=5)
                data = response.json()
                if data.get("status") == "OK":
                    results = []
                    for item in data.get("results", [])[:limit]:
                        results.append({
                            "name": item.get("name"),
                            "category": item.get("types", ["attraction"])[0],
                            "lat": item["geometry"]["location"]["lat"],
                            "lng": item["geometry"]["location"]["lng"]
                        })
                    return results
        except Exception as e:
            logger.error(f"Places search error for {query} in {destination}: {e}")
            
    # Mock fallback
    logger.warning(f"Using mock places search for {query} in {destination}")
    center = geocode(destination)
    import random
    results = []
    categories = query.split()
    cat = categories[0] if categories else "attraction"
    for i in range(limit):
        results.append({
            "name": f"{destination.capitalize()} {cat.capitalize()} {i+1}",
            "category": cat,
            "lat": center["lat"] + random.uniform(-0.03, 0.03),
            "lng": center["lng"] + random.uniform(-0.03, 0.03)
        })
    return results
