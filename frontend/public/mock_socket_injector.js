/**
 * Mock Socket Injector Utility
 * 
 * This script runs in the browser context and simulates sequential WebSocket events
 * emitted by the Python backend. Use this to style and verify the Next.js UI
 * independently of the Flask server.
 * 
 * Usage:
 * Call `window.injectMockEvents(session_id, destination)` in the browser console.
 */

(function () {
  console.log("Mock Socket Injector initialized. Call window.injectMockEvents(session_id, destination) to run a simulation.");

  const DESTINATIONS = {
    Japan: [139.6503, 35.6762],
    London: [-0.1278, 51.5074],
    Paris: [2.3522, 48.8566],
    NewYork: [-74.0060, 40.7128],
  };

  const AIRPORTS = {
    Japan: "NRT",
    London: "LHR",
    Paris: "CDG",
    NewYork: "JFK",
  };

  window.injectMockEvents = function (sessionId = "mock-session-123", destination = "Japan") {
    console.log(`Starting mock injector for session: ${sessionId}, destination: ${destination}`);
    
    dispatchMockEvent("connect", { data: "Connected via Mock Injector" });
    dispatchMockEvent("join_response", { status: "success", room: sessionId });

    const destCoords = DESTINATIONS[destination] || DESTINATIONS.Japan;
    const originCoords = [-122.4194, 37.7749]; // San Francisco
    const destCode = AIRPORTS[destination] || "NRT";

    const baseCost = 220.00;

    // 3 Outbound Options
    const outboundOptions = [
      {
        id: "out-direct-1",
        carrier: "ZipAir (Direct)",
        origin: originCoords,
        destination: destCoords,
        cost: baseCost,
        skyscanner_link: `https://www.skyscanner.com/transport/flights/sfo/${destCode.toLowerCase()}/2026-08-12/?adults=1&cabinclass=economy`
      },
      {
        id: "out-layover-2",
        carrier: "United Airlines (1 Layover)",
        origin: originCoords,
        destination: destCoords,
        cost: baseCost * 0.75,
        skyscanner_link: `https://www.skyscanner.com/transport/flights/sfo/${destCode.toLowerCase()}/2026-08-12/?adults=1&cabinclass=economy`
      },
      {
        id: "out-premium-3",
        carrier: "JAL Premium (Direct)",
        origin: originCoords,
        destination: destCoords,
        cost: baseCost * 1.5,
        skyscanner_link: `https://www.skyscanner.com/transport/flights/sfo/${destCode.toLowerCase()}/2026-08-12/?adults=1&cabinclass=economy`
      }
    ];

    // 3 Inbound Options
    const inboundOptions = [
      {
        id: "in-direct-1",
        carrier: "ZipAir Return (Direct)",
        origin: destCoords,
        destination: originCoords,
        cost: baseCost,
        skyscanner_link: `https://www.skyscanner.com/transport/flights/${destCode.toLowerCase()}/sfo/2026-08-19/?adults=1&cabinclass=economy`
      },
      {
        id: "in-layover-2",
        carrier: "United Return (1 Layover)",
        origin: destCoords,
        destination: originCoords,
        cost: baseCost * 0.8,
        skyscanner_link: `https://www.skyscanner.com/transport/flights/${destCode.toLowerCase()}/sfo/2026-08-19/?adults=1&cabinclass=economy`
      },
      {
        id: "in-premium-3",
        carrier: "JAL Return Premium (Direct)",
        origin: destCoords,
        destination: originCoords,
        cost: baseCost * 1.4,
        skyscanner_link: `https://www.skyscanner.com/transport/flights/${destCode.toLowerCase()}/sfo/2026-08-19/?adults=1&cabinclass=economy`
      }
    ];

    // 3 Hotel Options
    const loc1 = [destCoords[0] + 0.015, destCoords[1] + 0.015];
    const loc2 = [destCoords[0] - 0.012, destCoords[1] + 0.010];
    const loc3 = [destCoords[0] + 0.005, destCoords[1] - 0.015];
    
    const hotelOptions = [
      {
        id: "hotel-std-1",
        hotel_name: `Hotel Cozy in ${destination}`,
        location: loc1,
        cost: 110.00
      },
      {
        id: "hotel-lux-2",
        hotel_name: `Grand Imperial Resort (${destination})`,
        location: loc2,
        cost: 240.00
      },
      {
        id: "hotel-bgt-3",
        hotel_name: `Backpacker Zen Hostel (${destination})`,
        location: loc3,
        cost: 50.00
      }
    ];

    // Itinerary list
    const itinerary = [
      {day: 1, title: "Arrival & Check-in", desc: `Arrive in ${destination}, check in to hotel. Rest and explore local streets.`},
      {day: 2, title: "City Wonders & Landmarks", desc: `Visit top-rated sightseeing structures, temples, and viewing towers.`},
      {day: 3, title: "Local Market & Food Walk", desc: "Join an local food guide to try authentic dishes and visit central markets."},
      {day: 4, title: "Museums & Parks", desc: "Spend the day enjoying scenic parks and cultural museums."},
      {day: 5, title: "Return Journey SFO", desc: "Checkout and transfer back to the airport for your return flight home."}
    ];

    // Outbound Flight Lock (after 1s)
    setTimeout(() => {
      console.log("Mock Outbound Flight Locked...");
      dispatchMockEvent("outbound_flight_locked", {
        options: outboundOptions,
        selected_idx: 0,
        cost: outboundOptions[0].cost,
        remaining_budget: 1000 - outboundOptions[0].cost
      });
    }, 1000);

    // Inbound Flight Lock (after 2s)
    setTimeout(() => {
      console.log("Mock Inbound Flight Locked...");
      dispatchMockEvent("inbound_flight_locked", {
        options: inboundOptions,
        selected_idx: 0,
        cost: inboundOptions[0].cost,
        remaining_budget: 1000 - outboundOptions[0].cost - inboundOptions[0].cost
      });
    }, 2200);

    // Hotel Lock (after 3.5s)
    setTimeout(() => {
      console.log("Mock Hotel Locked...");
      dispatchMockEvent("hotel_locked", {
        options: hotelOptions,
        selected_idx: 0,
        cost: hotelOptions[0].cost,
        remaining_budget: 1000 - outboundOptions[0].cost - inboundOptions[0].cost - hotelOptions[0].cost
      });
    }, 3500);

    // Itinerary Lock (after 4.5s)
    setTimeout(() => {
      console.log("Mock Itinerary Locked...");
      dispatchMockEvent("itinerary_locked", { itinerary: itinerary });
    }, 4500);

    // Plan Completed (after 5.5s)
    setTimeout(() => {
      console.log("Mock Plan Completed...");
      const finalRemaining = 1000 - outboundOptions[0].cost - inboundOptions[0].cost - hotelOptions[0].cost;
      dispatchMockEvent("plan_completed", {
        summary: `Mock trip to ${destination} successfully planned! Outbound ZIPAIR, Inbound ZIPAIR Return, Hotel Cozy booked. All items are within budget.`,
        remaining_budget: finalRemaining
      });
    }, 5500);
  };

  function dispatchMockEvent(eventName, data) {
    const event = new CustomEvent("mock-socket-event", {
      detail: { event: eventName, data: data }
    });
    window.dispatchEvent(event);
  }
})();
