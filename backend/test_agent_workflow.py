import sys
import os
import time
from dotenv import load_dotenv

# Load env variables from backend/.env
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Reconfigure stdout to support unicode emojis on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Add parent directory to sys.path so backend module is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend import gemini_agent
from backend import firebase_state

def test_workflow():
    print("=== Testing Agent Workflow ===")
    
    session_id = "test-session-123"
    user_text = "Plan a trip from Jakarta to Tokyo with a budget of 1500 USD"
    
    print(f"Initializing session {session_id}...")
    firebase_state.initialize_session(session_id, 1500.0, "USD", "$")
    
    print("Running agent workflow...")
    # This runs the full pipeline synchronously
    gemini_agent.run_agent_workflow(user_text, session_id, None, 1500.0)
    
    print("\nRetrieving final session state...")
    session = firebase_state.get_session(session_id)
    
    print("\n=== Final Session Data ===")
    print(f"Total Budget: {session.get('total_budget')}")
    print(f"Remaining Budget: {session.get('remaining_budget')}")
    
    print("\nOutbound Options:")
    for opt in session.get("outbound_options", [])[:3]:
        print(f"  - {opt['carrier']}: {opt['cost']} ({opt['source']})")
        
    print("\nSelected Outbound Index:", session.get("selected_outbound_idx"))
    
    print("\nHotel Options:")
    for opt in session.get("hotel_options", [])[:3]:
        print(f"  - {opt['hotel_name']}: {opt['cost']} ({opt['source']})")
        
    print("\nSelected Hotel Index:", session.get("selected_hotel_idx"))
    
    print("\nItinerary:")
    for day in session.get("itinerary", []):
        print(f"  Day {day['day']}: {day['title']}")
        print(f"    {day['desc']}")
        
    print("\n=== Testing Complete ===")

if __name__ == "__main__":
    test_workflow()
