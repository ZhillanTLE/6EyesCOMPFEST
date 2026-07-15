import sys
import os
from dotenv import load_dotenv

# Load env variables from backend/.env
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

# Reconfigure stdout to support unicode emojis on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Add parent directory to sys.path so backend module is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend import skyscanner_gds
import requests

def test_weather():
    print("\n=== Testing wttr.in Weather API ===")
    try:
        url = "https://wttr.in/Tokyo?format=3"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        print(f"wttr.in Weather Success: {resp.text.strip()}")
    except Exception as e:
        print(f"wttr.in Weather Failed: {e}")

import logging
logging.basicConfig(level=logging.INFO)

def test_keys():
    print("\n=== Testing API Key Configuration ===")
    rapid_key = os.environ.get("RAPIDAPI_KEY")
    print(f"RAPIDAPI_KEY: {'CONFIGURED' if rapid_key else 'MISSING (will mock)'}")
    if rapid_key:
        print(f"  Raw value length: {len(rapid_key)}")
        print(f"  Raw value representation: {repr(rapid_key)}")

def test_flights():
    print("\n=== Testing Flight Search ===")
    try:
        # Search flights from SFO to NRT in USD
        res = skyscanner_gds.mock_gds_search_flights("SFO", "NRT", "USD", "outbound", 1000.0)
        print(f"Flight Results (Count: {len(res)}):")
        for item in res[:3]:
            print(f"  - {item['carrier']}: {item['cost']} ({item['source']})")
    except Exception as e:
        print(f"Flight Search Failed: {e}")

def test_hotels():
    print("\n=== Testing Hotel Search ===")
    try:
        # Search hotels in NRT (Tokyo Narita area) or TOK in USD
        res = skyscanner_gds.mock_gds_search_hotels("Tokyo", "USD", 1000.0, "NRT")
        print(f"Hotel Results (Count: {len(res)}):")
        for item in res[:3]:
            print(f"  - {item['hotel_name']}: {item['cost']} ({item['source']})")
    except Exception as e:
        print(f"Hotel Search Failed: {e}")

def test_pois():
    print("\n=== Testing POI Search ===")
    try:
        # Tokyo coordinates (approx)
        res = skyscanner_gds.mock_gds_search_pois(35.6762, 139.6503)
        print(f"POI Results (Count: {len(res)}):")
        for item in res[:3]:
            print(f"  - {item['name']} ({item['category']})")
    except Exception as e:
        print(f"POI Search Failed: {e}")

if __name__ == "__main__":
    print("Starting Travel GDS API & Fallback Tests...")
    test_weather()
    test_keys()
    test_flights()
    test_hotels()
    test_pois()
    print("\nTests finished.")
