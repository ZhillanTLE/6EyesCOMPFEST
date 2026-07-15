import os
import json
import logging
import hashlib
from typing import List, Optional
import google.generativeai as genai
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Simple in-memory cache for FR2
_parse_cache = {}

class TripRequest(BaseModel):
    origin_city: Optional[str] = Field(description="The origin city name")
    destination_city: Optional[str] = Field(description="The destination city name")
    start_date: Optional[str] = Field(description="The start date in ISO format (YYYY-MM-DD), if provided")
    end_date: Optional[str] = Field(description="The end date in ISO format (YYYY-MM-DD), if provided")
    duration_days: Optional[int] = Field(description="The intended duration of the trip in days, if provided")
    travelers: int = Field(description="Number of travelers. Default is 1 if unspecified.")
    total_budget: Optional[float] = Field(description="The total numeric budget for the trip.")
    currency: str = Field(description="The 3-letter currency code, default to 'USD' if unknown.")
    interests: List[str] = Field(description="A list of interests or activities mentioned (e.g. ['beaches', 'food'])")
    trip_style: Optional[str] = Field(description="The style of the trip (e.g. 'budget', 'luxury', 'romantic')")
    notes: Optional[str] = Field(description="Any extra notes or constraints")
    is_valid: bool = Field(description="True if both origin and destination are present and unambiguously identified.")
    clarification_needed: Optional[str] = Field(description="If is_valid is false, this string should ask the user for the missing critical information (e.g. 'Where are you departing from?').")
    
    # Backend specific fields
    currency_symbol: Optional[str] = Field(description="The symbol for the currency (e.g. '$', 'Rp', '€').")

def parse_trip_request(user_text: str) -> dict:
    """
    Parse free-form user text into a structured TripRequest using Gemini API.
    Returns a dictionary matching the TripRequest schema.
    """
    # Check cache (FR2)
    req_hash = hashlib.md5(user_text.encode('utf-8')).hexdigest()
    if req_hash in _parse_cache:
        logger.info(f"Returning cached parse result for: {user_text[:30]}...")
        return _parse_cache[req_hash]

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY is not set. Falling back to mock mode.")
        return _fallback_regex_parse(user_text)
        
    genai.configure(api_key=api_key)
    
    # We use gemini-flash-latest with structured JSON output via config
    model = genai.GenerativeModel(
        "gemini-flash-latest",
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.1
        )
    )
    
    schema_str = TripRequest.schema_json()
    
    prompt = f"""
    You are an expert travel assistant. Parse the following user trip request into a structured JSON object.
    You MUST return ONLY a JSON object that strictly adheres to the following JSON schema:
    {schema_str}
    
    Extract the origin, destination, budget, dates, and other preferences.
    If the origin or destination is missing or highly ambiguous, set `is_valid` to false and provide a friendly `clarification_needed` message asking for the missing info.
    If the budget is missing, you can leave it null but try to extract any numbers that look like budgets.
    
    User Request: "{user_text}"
    """
    
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # DeepSeek might still include markdown blocks sometimes
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("\n", 1)[0].strip()
        if text.startswith("json"):
            text = text[4:].strip()
            
        data = json.loads(text)
        logger.info(f"Successfully parsed trip request: {data}")
        
        # Store in cache
        _parse_cache[req_hash] = data
        return data
    except Exception as e:
        logger.error(f"Failed to parse trip request with DeepSeek: {e}")
        return _fallback_regex_parse(user_text)

def _fallback_regex_parse(user_text: str) -> dict:
    """Simple regex fallback to keep app functional during local dev or quota limits (FR3)."""
    import re
    fallback_data = {
        "origin_city": None,
        "destination_city": None,
        "start_date": None,
        "end_date": None,
        "duration_days": 3,
        "travelers": 1,
        "total_budget": 2000,
        "currency": "USD",
        "interests": [],
        "trip_style": None,
        "notes": None,
        "is_valid": False,
        "clarification_needed": "A backend error occurred while parsing your request. Please try again.",
        "currency_symbol": "$"
    }
    
    try:
        # Extract origin and destination
        loc_match = re.search(r'(?:from\s+)?([a-zA-Z\s]+?)\s+to\s+([a-zA-Z\s]+?)(?:,|\s+for|\s+\d|$)', user_text, re.IGNORECASE)
        if loc_match:
            o, d = loc_match.groups()
            # Clean up extracted strings
            o = o.replace("plan a trip", "").strip()
            o = ' '.join(o.split()) # normalize spaces
            if o and d:
                fallback_data["origin_city"] = o
                fallback_data["destination_city"] = d.strip()
                fallback_data["is_valid"] = True
                fallback_data["clarification_needed"] = None
                
        # Extract budget
        b_match = re.search(r'\$(\d+)', user_text)
        if b_match:
            fallback_data["total_budget"] = float(b_match.group(1))
            
        # Extract duration
        d_match = re.search(r'(\d+)\s+days?', user_text, re.IGNORECASE)
        if d_match:
            fallback_data["duration_days"] = int(d_match.group(1))
            
        # Extract travelers
        t_match = re.search(r'(\d+)\s+people?', user_text, re.IGNORECASE)
        if t_match:
            fallback_data["travelers"] = int(t_match.group(1))
            
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Regex parsing failed: {e}")
        
    return fallback_data
