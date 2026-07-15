import os
import sys
import unittest
from dotenv import load_dotenv

# Load env variables before importing parser
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from backend.nlp_parser import parse_trip_request

class TestNLPParser(unittest.TestCase):
    
    def test_valid_request(self):
        text = "$1650 jakarta to tokyo 26-30 December 2026"
        res = parse_trip_request(text)
        
        self.assertTrue(res.get("is_valid"))
        self.assertEqual(res.get("origin_iata"), "CGK")
        # Could be NRT or HND, so we check if it's one of them or if it exists
        self.assertIn(res.get("destination_iata"), ["NRT", "HND"])
        self.assertEqual(res.get("total_budget"), 1650.0)
        self.assertEqual(res.get("currency"), "USD") # USD is default for $
        
    def test_missing_destination(self):
        text = "I have $2000 and want to fly out of JFK but I don't know where to go."
        res = parse_trip_request(text)
        
        self.assertFalse(res.get("is_valid"))
        self.assertIsNotNone(res.get("clarification_needed"))
        self.assertEqual(res.get("origin_iata"), "JFK")
        self.assertIsNone(res.get("destination_iata"))

    def test_ambiguous_request(self):
        text = "budget trip to Bali in December for 2 people, love beaches and food"
        res = parse_trip_request(text)
        
        # Missing origin, so it should be invalid
        self.assertFalse(res.get("is_valid"))
        self.assertIsNotNone(res.get("clarification_needed"))
        self.assertEqual(res.get("travelers"), 2)
        self.assertEqual(res.get("destination_iata"), "DPS") # Bali
        # check interests
        self.assertIn("beaches", [i.lower() for i in res.get("interests", [])])

    def test_multi_lingual(self):
        text = "15000000 rupiah dari jakarta ke singapura buat 2 orang"
        res = parse_trip_request(text)
        
        self.assertTrue(res.get("is_valid"))
        self.assertEqual(res.get("origin_iata"), "CGK")
        self.assertEqual(res.get("destination_iata"), "SIN")
        self.assertEqual(res.get("total_budget"), 15000000.0)
        self.assertEqual(res.get("currency"), "IDR")
        self.assertEqual(res.get("travelers"), 2)

if __name__ == "__main__":
    unittest.main()
