import unittest
import os
import sys
from dotenv import load_dotenv

# Ensure the backend module can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

from backend.nlp_parser import parse_trip_request
from unittest.mock import patch, MagicMock
import json

class TestNLPParserRegression(unittest.TestCase):
    
    @patch('backend.nlp_parser.genai.GenerativeModel.generate_content')
    def test_valid_queries(self, mock_generate_content):
        # A suite of previously working query formats that regressed
        queries = [
            "$2000 jakarta to tokyo 3 days trip",
            "jakarta to tokyo, 3 days, $2000 budget",
            "plan a trip from jakarta to tokyo for 3 days"
        ]
        
        for query in queries:
            with self.subTest(query=query):
                # Mock a successful extraction
                mock_response = MagicMock()
                mock_response.text = json.dumps({
                    "origin_city": "Jakarta",
                    "destination_city": "Tokyo",
                    "duration_days": 3,
                    "is_valid": True
                })
                mock_generate_content.return_value = mock_response

                result = parse_trip_request(query)
                self.assertTrue(result["is_valid"], f"Failed to parse valid query: {query}")
                self.assertIsNotNone(result.get("origin_city"), f"Origin missing in {query}")
                self.assertIsNotNone(result.get("destination_city"), f"Destination missing in {query}")
                
                # Check for "jakarta" in origin (case-insensitive)
                self.assertIn("jakarta", result["origin_city"].lower(), f"Origin extracted incorrectly: {result['origin_city']}")
                # Check for "tokyo" in destination (case-insensitive)
                self.assertIn("tokyo", result["destination_city"].lower(), f"Destination extracted incorrectly: {result['destination_city']}")
                
                # Ensure it extracts duration
                self.assertEqual(result.get("duration_days"), 3, f"Duration missing or incorrect in {query}")

    @patch('backend.nlp_parser.genai.GenerativeModel.generate_content')
    def test_missing_info_queries(self, mock_generate_content):
        # Partial info cases should set is_valid = False and ask for clarification
        queries = [
            "I want to go to Tokyo for 3 days", # missing origin
            "I want to fly from Jakarta for a week" # missing destination
        ]
        
        for query in queries:
            with self.subTest(query=query):
                # Mock a missing info response
                mock_response = MagicMock()
                mock_response.text = json.dumps({
                    "origin_city": None,
                    "destination_city": "Tokyo",
                    "is_valid": False,
                    "clarification_needed": "Where are you departing from?"
                })
                mock_generate_content.return_value = mock_response

                result = parse_trip_request(query)
                self.assertFalse(result["is_valid"], f"Invalid query was marked valid: {query}")
                self.assertIsNotNone(result.get("clarification_needed"), "Missing clarification prompt")

    @patch('backend.nlp_parser.genai.GenerativeModel.generate_content')
    def test_exception_handling(self, mock_generate_content):
        # Simulating a quota limit or JSON parse failure
        mock_generate_content.side_effect = Exception("429 Quota Exceeded")
        
        result = parse_trip_request("jakarta to tokyo 3 days")
        
        self.assertFalse(result["is_valid"])
        self.assertEqual(
            result.get("clarification_needed"),
            "A backend error occurred while parsing your request. Please try again."
        )

if __name__ == '__main__':
    unittest.main()
