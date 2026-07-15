import unittest
import math
from backend import places_api
from backend.gemini_agent import generate_itinerary, agent_context

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat/2) * math.sin(dLat/2) + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon/2) * math.sin(dLon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

class TestItineraryAndRanking(unittest.TestCase):
    def test_hotel_proximity_ranking(self):
        # Given a centroid
        centroid = {"lat": 35.6762, "lng": 139.6503}
        
        # And hotel candidates
        candidates = [
            {"hotel_name": "Far Hotel", "location": [139.7503, 35.7762], "cost": 100}, # Far (0.1 deg away)
            {"hotel_name": "Close Hotel", "location": [139.6603, 35.6862], "cost": 120}, # Close (0.01 deg away)
            {"hotel_name": "Expensive Close Hotel", "location": [139.6603, 35.6862], "cost": 500}, # Close but over budget
        ]
        
        max_budget = 200
        
        for h in candidates:
            h["distance_km"] = haversine(centroid["lat"], centroid["lng"], h["location"][1], h["location"][0])
            
        # Sort by distance and budget fit
        candidates.sort(key=lambda x: (x["distance_km"], abs(x["cost"] - max_budget)))
        
        # Close Hotel should be first
        self.assertEqual(candidates[0]["hotel_name"], "Close Hotel")
        
        # Far Hotel should be further than Close Hotel
        self.assertGreater(candidates[2]["distance_km"], candidates[0]["distance_km"])
        
    def test_fallback_itinerary_structure(self):
        # Without API key, it should use fallback
        import os
        old_key = os.environ.get("GEMINI_API_KEY")
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]
            
        agent_context.trip_entities = {"interests": ["food"], "days": 3}
        itinerary = generate_itinerary("Tokyo", 500.0)
        
        self.assertIsInstance(itinerary, list)
        self.assertGreaterEqual(len(itinerary), 1)
        
        day1 = itinerary[0]
        self.assertIn("day", day1)
        self.assertIn("spots", day1)
        
        spots = day1["spots"]
        self.assertIsInstance(spots, list)
        if len(spots) > 0:
            spot1 = spots[0]
            self.assertIn("lat", spot1)
            self.assertIn("lng", spot1)
            self.assertIn("name", spot1)
            
        if old_key is not None:
            os.environ["GEMINI_API_KEY"] = old_key

if __name__ == "__main__":
    unittest.main()
