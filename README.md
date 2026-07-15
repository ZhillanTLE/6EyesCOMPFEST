# 6Eyes Architecture

## Agent Workflow

The core planning workflow orchestrated in `gemini_agent.py` has been updated to the following order:

1. **Itinerary Generation**: 
   The system extracts trip parameters from the user's natural language request. It then generates a detailed, day-by-day itinerary using a Gemini agent. Crucially, the agent now pulls real geographic POIs by calling `places_api` tools (`search_places` and `geocode`) to retrieve real-world coordinates and pricing for activities.

2. **Hotel Selection & Ranking**: 
   Once the itinerary is built, the system computes the geographical centroid (average lat/lng) of all the scheduled activities. Hotel candidates (from the mock/GDS or Tripadvisor) are then geocoded and ranked based on their Haversine distance to this centroid, with budget fit as a secondary tie-breaker. This ensures the user stays close to their planned activities.

3. **Flights**: 
   Flights are retrieved and locked in to match the remaining budget and the destination requirements.

## Map Rendering

The frontend UI (specifically `MapCanvas.tsx`) renders a continuous polyline route visualizing the entire trip rather than disconnected markers. The path connects:
`Origin Airport -> Destination Airport -> Hotel -> Itinerary Spots (all days in chronological order) -> Hotel -> Origin Airport (Return Flight)`
