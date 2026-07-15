"use client";

import React, { useState, useEffect, useRef } from "react";
import io, { Socket } from "socket.io-client";
import BudgetTracker from "@/components/BudgetTracker";
import MapCanvas from "@/components/MapCanvas";
import ControlPanel from "@/components/ControlPanel";
import { Sparkles, CheckCircle2, PlaneTakeoff, PlaneLanding, Hotel, Calendar, ExternalLink, Clock, MapPin } from "lucide-react";
import { getIdToken } from "@/lib/auth";

const GOOGLE_MAPS_API_KEY = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || "";
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:5000";

export default function Home() {
  const [totalBudget, setTotalBudget] = useState<number | null>(null);
  const [remainingBudget, setRemainingBudget] = useState<number | null>(null);
  const [currency, setCurrency] = useState("USD");
  const [currencySymbol, setCurrencySymbol] = useState("$");
  
  // Option lists from server
  const [outboundOptions, setOutboundOptions] = useState<any[]>([]);
  const [inboundOptions, setInboundOptions] = useState<any[]>([]);
  const [hotelOptions, setHotelOptions] = useState<any[]>([]);
  const [itinerary, setItinerary] = useState<any[]>([]);

  // Selected Indices
  const [selectedOutboundIdx, setSelectedOutboundIdx] = useState<number>(0);
  const [selectedInboundIdx, setSelectedInboundIdx] = useState<number>(0);
  const [selectedHotelIdx, setSelectedHotelIdx] = useState<number>(0);

  // Swap panels visibility toggles
  const [showOutboundSwap, setShowOutboundSwap] = useState(false);
  const [showInboundSwap, setShowInboundSwap] = useState(false);
  const [showHotelSwap, setShowHotelSwap] = useState(false);
  
  const [isLoading, setIsLoading] = useState(false);
  const [statusText, setStatusText] = useState("");
  const [finalSummary, setFinalSummary] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState<string>("parsing");

  type StepState = "pending" | "in_progress" | "done" | "failed";
  interface PlanStep {
    state: StepState;
    message: string;
  }
  const initialSteps: Record<string, PlanStep> = {
    parsing: { state: "pending", message: "Parsing Request" },
    flights: { state: "pending", message: "Searching Flights" },
    budget: { state: "pending", message: "Checking Budget" },
    hotels: { state: "pending", message: "Searching Hotels" },
    itinerary: { state: "pending", message: "Building Itinerary" },
    finalize: { state: "pending", message: "Finalizing" }
  };
  const [planSteps, setPlanSteps] = useState<Record<string, PlanStep>>(initialSteps);

  const socketRef = useRef<Socket | null>(null);
  const sessionIdRef = useRef<string>("");

  const activeOutbound = outboundOptions[selectedOutboundIdx] || null;
  const activeInbound = inboundOptions[selectedInboundIdx] || null;
  const activeHotel = hotelOptions[selectedHotelIdx] || null;

  // Formatting helper for currency sensitivity
  const formatPrice = (val: number | null) => {
    if (val === null) return "";
    if (currency === "IDR") {
      return `Rp ${val.toLocaleString("id-ID", { maximumFractionDigits: 0 })}`;
    }
    if (currency === "JPY") {
      return `¥${val.toLocaleString("ja-JP", { maximumFractionDigits: 0 })}`;
    }
    if (currency === "CNY") {
      return `¥${val.toLocaleString("zh-CN", { maximumFractionDigits: 0 })}`;
    }
    if (currency === "EUR") {
      return `€${val.toLocaleString("de-DE", { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;
    }
    return `${currencySymbol}${val.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;
  };

  // Initialize socket connection
  const initSocket = () => {
    if (socketRef.current) return;

    console.log("Connecting to WebSocket backend at:", BACKEND_URL);
    const socket = io(BACKEND_URL, {
      transports: ["polling", "websocket"],
      reconnectionAttempts: 5,
    });

    socket.on("connect", () => {
      console.log("Connected to WebSocket server.");
    });

    socket.on("join_response", (data) => {
      console.log("Successfully joined Socket room:", data);
    });

    socket.on("outbound_flight_locked", (data) => {
      console.log("Socket: Outbound flight options locked:", data);
      setOutboundOptions(data.options || []);
      setSelectedOutboundIdx(data.selected_idx ?? 0);
      setRemainingBudget(data.remaining_budget);
      setStatusText("Outbound flight locked!");
    });

    socket.on("inbound_flight_locked", (data) => {
      console.log("Socket: Inbound flight options locked:", data);
      setInboundOptions(data.options || []);
      setSelectedInboundIdx(data.selected_idx ?? 0);
      setRemainingBudget(data.remaining_budget);
      setStatusText("Inbound return flight locked!");
    });

    socket.on("hotel_locked", (data) => {
      console.log("Socket: Hotel options locked:", data);
      setHotelOptions(data.options || []);
      setSelectedHotelIdx(data.selected_idx ?? 0);
      setRemainingBudget(data.remaining_budget);
      setStatusText("Hotels locked successfully!");
    });

    socket.on("agent_progress", (data) => {
      console.log("Socket: Agent Progress status:", data);
      if (data.status) {
        setStatusText(data.status);
      }
    });

    socket.on("step_progress", (data) => {
      console.log("Socket: Step Progress:", data);
      const { step, state, message } = data;
      setPlanSteps((prev) => ({
        ...prev,
        [step]: { state, message }
      }));
      if (state === "in_progress") {
        setCurrentStep(step);
      }
      if (message) {
        setStatusText(message);
      }
    });

    socket.on("itinerary_progress", (data) => {
      console.log("Socket: Itinerary progress:", data);
      setPlanSteps((prev) => ({
        ...prev,
        itinerary: { state: "in_progress", message: `Building Itinerary - Day ${data.day} of ${data.total_days} planned` }
      }));
      setItinerary((prev) => {
        const existing = prev.filter(item => item.day !== data.day);
        const next = [...existing, data.data];
        return next.sort((a, b) => a.day - b.day);
      });
      setStatusText(`Building Itinerary - Day ${data.day} of ${data.total_days} planned`);
    });

    socket.on("itinerary_locked", (data) => {
      console.log("Socket: Daily Itinerary locked:", data);
      setItinerary(data.itinerary || []);
    });

    socket.on("item_swapped", (data) => {
      console.log("Socket: Broadcast swap update received:", data);
      const { item_type, option_index, remaining_budget } = data;
      setRemainingBudget(remaining_budget);
      if (item_type === "outbound") {
        setSelectedOutboundIdx(option_index);
      } else if (item_type === "inbound") {
        setSelectedInboundIdx(option_index);
      } else if (item_type === "hotel") {
        setSelectedHotelIdx(option_index);
      }
    });

    socket.on("plan_completed", (data) => {
      console.log("Socket: Trip Plan completed:", data);
      setIsLoading(false);
      setStatusText("Plan complete!");
      setFinalSummary(data.summary);
      if (data.remaining_budget !== undefined) {
        setRemainingBudget(data.remaining_budget);
      }
    });

    socket.on("plan_error", (data) => {
      console.log("Socket: Trip Plan error:", data);
      setIsLoading(false);
      setStatusText("Error: " + data.error);
      setFinalSummary("I need more information to plan this trip: " + data.error);
      setPlanSteps((prev) => {
        // Find the first in_progress or pending step and mark it failed
        const newSteps = { ...prev };
        for (const key of Object.keys(newSteps)) {
          if (newSteps[key].state === "in_progress" || newSteps[key].state === "pending") {
            newSteps[key].state = "failed";
            newSteps[key].message = data.error;
            break;
          }
        }
        return newSteps;
      });
    });

    socket.on("disconnect", () => {
      console.log("Disconnected from WebSocket server.");
    });

    socketRef.current = socket;
  };

  useEffect(() => {
    // Initialize real socket connection
    initSocket();

    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
        socketRef.current = null;
      }
    };
  }, []);

  // Stuck-state safety net (FR4)
  useEffect(() => {
    if (!isLoading) return;

    let stuckTimer: NodeJS.Timeout | null = null;
    
    // Find if there is an in_progress step
    const inProgressStep = Object.entries(planSteps).find(([_, stepData]) => stepData.state === "in_progress");
    
    if (inProgressStep) {
      const [stepName] = inProgressStep;
      stuckTimer = setTimeout(() => {
        setStatusText("Still working - finalizing details...");
        if (stepName === "itinerary") {
          setPlanSteps(prev => ({
            ...prev,
            itinerary: { ...prev.itinerary, message: "Still working - finalizing day-by-day plans..." }
          }));
        }
      }, 8000); // 8 second safety net
    }

    return () => {
      if (stuckTimer) clearTimeout(stuckTimer);
    };
  }, [planSteps, isLoading]);

  // Handle plan submit POST request
  const handlePlanTrip = async (prompt: string, isDemo: boolean = false) => {
    setIsLoading(true);
    setStatusText("Analyzing your trip request...");
    setFinalSummary(null);
    setOutboundOptions([]);
    setInboundOptions([]);
    setHotelOptions([]);
    setItinerary([]);
    setSelectedOutboundIdx(0);
    setSelectedInboundIdx(0);
    setSelectedHotelIdx(0);
    setShowOutboundSwap(false);
    setShowInboundSwap(false);
    setShowHotelSwap(false);
    setPlanSteps(initialSteps);

    const session = "sess-" + Math.random().toString(36).substring(2, 9);
    sessionIdRef.current = session;

    if (socketRef.current) {
      socketRef.current.emit("join_session", { session_id: session });
    }

    try {
      const idToken = await getIdToken();
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (idToken) headers["Authorization"] = `Bearer ${idToken}`;
      const response = await fetch(`${BACKEND_URL}/api/plan-trip`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          user_text: prompt,
          session_id: session,
          isDemo,
        }),
      });

      if (!response.ok) {
        throw new Error(`Server returned error status: ${response.status}`);
      }

      const data = await response.json();
      console.log("POST /api/plan-trip success:", data);
      
      setTotalBudget(data.initial_budget);
      setRemainingBudget(data.initial_budget);
      setCurrency(data.currency || "USD");
      setCurrencySymbol(data.currency_symbol || "$");
      setStatusText("Trip plan initiated. Starting agent workflow...");
    } catch (err: any) {
      console.error("Failed to plan trip via Flask backend:", err);
      setStatusText(`Connection failed. Please ensure the backend is running.`);
      setPlanSteps((prev) => {
        const newSteps = { ...prev };
        for (const key of Object.keys(newSteps)) {
          if (newSteps[key].state === "in_progress" || newSteps[key].state === "pending") {
            newSteps[key].state = "failed";
            newSteps[key].message = "Connection failed";
            break;
          }
        }
        return newSteps;
      });
      setIsLoading(false);
    }
  };

  // Modular Swapping Handler
  const handleSwapItem = async (itemType: "outbound" | "inbound" | "hotel", optionIndex: number) => {
    // 1. Calculate budget changes locally for rapid UI response
    let updatedOutbound = selectedOutboundIdx;
    let updatedInbound = selectedInboundIdx;
    let updatedHotel = selectedHotelIdx;

    if (itemType === "outbound") {
      updatedOutbound = optionIndex;
      setSelectedOutboundIdx(optionIndex);
    } else if (itemType === "inbound") {
      updatedInbound = optionIndex;
      setSelectedInboundIdx(optionIndex);
    } else if (itemType === "hotel") {
      updatedHotel = optionIndex;
      setSelectedHotelIdx(optionIndex);
    }

    const outboundCost = outboundOptions[updatedOutbound]?.cost ?? 0.0;
    const inboundCost = inboundOptions[updatedInbound]?.cost ?? 0.0;
    const hotelCost = hotelOptions[updatedHotel]?.cost ?? 0.0;

    if (totalBudget !== null) {
      setRemainingBudget(totalBudget - (outboundCost + inboundCost + hotelCost));
    }

    // 2. Call backend swap endpoint to update session document state
    try {
      const response = await fetch(`${BACKEND_URL}/api/swap-item`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          session_id: sessionIdRef.current || "mock-session",
          item_type: itemType,
          option_index: optionIndex
        })
      });
      if (response.ok) {
        const data = await response.json();
        setRemainingBudget(data.remaining_budget);
        console.log(`Synced swap update successfully to backend: ${itemType} -> Option ${optionIndex}`);
      }
    } catch (err) {
      console.error("Failed to sync item swap with Flask backend:", err);
    }
  };

  const handleReset = () => {
    setTotalBudget(null);
    setRemainingBudget(null);
    setCurrency("USD");
    setCurrencySymbol("$");
    setOutboundOptions([]);
    setInboundOptions([]);
    setHotelOptions([]);
    setItinerary([]);
    setSelectedOutboundIdx(0);
    setSelectedInboundIdx(0);
    setSelectedHotelIdx(0);
    setShowOutboundSwap(false);
    setShowInboundSwap(false);
    setShowHotelSwap(false);
    setIsLoading(false);
    setStatusText("Session reset. Map cleared.");
    setFinalSummary(null);
    setPlanSteps(initialSteps);
  };

  const hasItineraryDetails = finalSummary !== null || itinerary.length > 0 || outboundOptions.length > 0 || inboundOptions.length > 0 || hotelOptions.length > 0;

  // Custom Hotel Link builder redirecting directly to the API-provided booking link
  const getHotelLink = (hotel: any) => {
    if (!hotel) return "#";
    return hotel.booking_link || `https://www.trip.com/hotels/list?searchText=${encodeURIComponent(hotel.hotel_name)}&curr=${currency}`;
  };

  return (
    <main className="relative w-screen h-screen overflow-hidden bg-zinc-950 font-sans text-white">
      {/* 1. Google Map Viewport */}
      <div className="absolute inset-0 z-0">
        <MapCanvas
          googleMapsApiKey={GOOGLE_MAPS_API_KEY}
          outboundFlight={activeOutbound}
          inboundFlight={activeInbound}
          hotelData={activeHotel}
          itinerary={itinerary}
          currentStep={currentStep}
        />
      </div>


      {/* 3. Budget Tracker Overlay */}
      <BudgetTracker
        totalBudget={totalBudget}
        remainingBudget={remainingBudget}
        currency={currency}
        currencySymbol={currencySymbol}
      />

      {/* 4. Unified Itinerary & Swap Center Drawer Panel */}
      {hasItineraryDetails && (
        <div className="absolute top-6 right-6 bottom-28 w-[380px] bg-zinc-950/90 backdrop-blur-md border border-zinc-850 rounded-xl p-5 shadow-2xl overflow-y-auto z-10 space-y-5 scrollbar-thin scrollbar-track-transparent scrollbar-thumb-zinc-800 transition-all duration-300">
          
          <div className="flex items-center gap-2 text-blue-400 font-bold text-sm border-b border-zinc-800/80 pb-2">
            <CheckCircle2 className="w-4 h-4" />
            <span>Itinerary & Swap Center</span>
          </div>

          {/* Swapping HUD Options */}
          <div className="space-y-4 pt-1">
            
            {/* Outbound Flights Swap Card */}
            {activeOutbound && (
              <div className="space-y-2">
                <div className="flex items-center gap-1 text-[10px] text-zinc-500 font-bold uppercase tracking-wider">
                  <PlaneTakeoff className="w-3.5 h-3.5" />
                  <span>Outbound Flight</span>
                </div>
                
                <div className="relative group bg-zinc-900/40 border border-zinc-800/80 rounded-xl p-3.5 transition-all duration-200 hover:border-zinc-700">
                  <div className="flex justify-between items-start">
                    <div className="space-y-0.5 pr-20">
                      <div className="text-zinc-200 font-sans font-semibold text-xs leading-normal">
                        {activeOutbound.carrier}
                      </div>
                      <div className="text-zinc-500 text-[10px] font-medium">
                        Locked Choice
                      </div>
                    </div>
                    <span className="text-sm font-mono font-bold text-white whitespace-nowrap">
                      {formatPrice(activeOutbound.cost)}
                    </span>
                  </div>

                  {/* Hover Buttons Overlay */}
                  <div className="absolute inset-0 bg-zinc-950/95 backdrop-blur-[2px] flex items-center justify-center gap-3 opacity-0 group-hover:opacity-100 transition-opacity duration-200 rounded-xl">
                    <button
                      onClick={() => setShowOutboundSwap(!showOutboundSwap)}
                      className="bg-zinc-800 hover:bg-zinc-700 text-white font-semibold text-xs px-3.5 py-1.5 rounded-lg transition-all cursor-pointer"
                    >
                      {showOutboundSwap ? "Close Swap" : "Swap"}
                    </button>
                    {activeOutbound.skyscanner_link && (
                      <a
                        href={activeOutbound.skyscanner_link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs px-3.5 py-1.5 rounded-lg transition-all flex items-center gap-1 cursor-pointer"
                      >
                        <span>Book</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>
                </div>

                {/* Dropdown Options for Outbound Swapping */}
                {showOutboundSwap && outboundOptions.length > 0 && (
                  <div className="bg-zinc-900/30 border border-zinc-850 rounded-xl p-2.5 space-y-1.5 animate-fade-in">
                    <div className="text-[9px] text-zinc-500 font-bold uppercase tracking-wider px-1">Alternate outbound choices:</div>
                    {outboundOptions.map((opt, i) => (
                      <label 
                        key={opt.id} 
                        className={`flex items-center justify-between p-2.5 rounded-lg border text-xs cursor-pointer transition-all duration-200 ${
                          selectedOutboundIdx === i 
                            ? "bg-blue-600/10 border-blue-500 text-white" 
                            : "bg-zinc-900/40 border-zinc-800/50 text-zinc-400 hover:bg-zinc-800/30"
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <input
                            type="radio"
                            name="outbound_flight"
                            checked={selectedOutboundIdx === i}
                            onChange={() => {
                              handleSwapItem("outbound", i);
                              setShowOutboundSwap(false);
                            }}
                            className="accent-blue-500 cursor-pointer"
                          />
                          <span className="font-sans font-medium text-[11px] leading-tight">{opt.carrier}</span>
                        </div>
                        <span className="font-mono font-semibold text-[11px] whitespace-nowrap">{formatPrice(opt.cost)}</span>
                      </label>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Inbound Flights Swap Card */}
            {activeInbound && (
              <div className="space-y-2">
                <div className="flex items-center gap-1 text-[10px] text-zinc-500 font-bold uppercase tracking-wider">
                  <PlaneLanding className="w-3.5 h-3.5" />
                  <span>Inbound return Flight</span>
                </div>
                
                <div className="relative group bg-zinc-900/40 border border-zinc-800/80 rounded-xl p-3.5 transition-all duration-200 hover:border-zinc-700">
                  <div className="flex justify-between items-start">
                    <div className="space-y-0.5 pr-20">
                      <div className="text-zinc-200 font-sans font-semibold text-xs leading-normal">
                        {activeInbound.carrier}
                      </div>
                      <div className="text-zinc-500 text-[10px] font-medium">
                        Locked Choice
                      </div>
                    </div>
                    <span className="text-sm font-mono font-bold text-white whitespace-nowrap">
                      {formatPrice(activeInbound.cost)}
                    </span>
                  </div>

                  {/* Hover Buttons Overlay */}
                  <div className="absolute inset-0 bg-zinc-950/95 backdrop-blur-[2px] flex items-center justify-center gap-3 opacity-0 group-hover:opacity-100 transition-opacity duration-200 rounded-xl">
                    <button
                      onClick={() => setShowInboundSwap(!showInboundSwap)}
                      className="bg-zinc-800 hover:bg-zinc-700 text-white font-semibold text-xs px-3.5 py-1.5 rounded-lg transition-all cursor-pointer"
                    >
                      {showInboundSwap ? "Close Swap" : "Swap"}
                    </button>
                    {activeInbound.skyscanner_link && (
                      <a
                        href={activeInbound.skyscanner_link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="bg-purple-600 hover:bg-purple-500 text-white font-semibold text-xs px-3.5 py-1.5 rounded-lg transition-all flex items-center gap-1 cursor-pointer"
                      >
                        <span>Book</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>
                </div>

                {/* Dropdown Options for Inbound Swapping */}
                {showInboundSwap && inboundOptions.length > 0 && (
                  <div className="bg-zinc-900/30 border border-zinc-850 rounded-xl p-2.5 space-y-1.5 animate-fade-in">
                    <div className="text-[9px] text-zinc-500 font-bold uppercase tracking-wider px-1">Alternate inbound choices:</div>
                    {inboundOptions.map((opt, i) => (
                      <label 
                        key={opt.id} 
                        className={`flex items-center justify-between p-2.5 rounded-lg border text-xs cursor-pointer transition-all duration-200 ${
                          selectedInboundIdx === i 
                            ? "bg-purple-600/10 border-purple-500 text-white" 
                            : "bg-zinc-900/40 border-zinc-800/50 text-zinc-400 hover:bg-zinc-800/30"
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <input
                            type="radio"
                            name="inbound_flight"
                            checked={selectedInboundIdx === i}
                            onChange={() => {
                              handleSwapItem("inbound", i);
                              setShowInboundSwap(false);
                            }}
                            className="accent-purple-500 cursor-pointer"
                          />
                          <span className="font-sans font-medium text-[11px] leading-tight">{opt.carrier}</span>
                        </div>
                        <span className="font-mono font-semibold text-[11px] whitespace-nowrap">{formatPrice(opt.cost)}</span>
                      </label>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Hotels Swap Card */}
            {activeHotel && (
              <div className="space-y-2">
                <div className="flex items-center gap-1 text-[10px] text-zinc-500 font-bold uppercase tracking-wider">
                  <Hotel className="w-3.5 h-3.5" />
                  <span>Accommodation</span>
                </div>
                
                <div className="relative group bg-zinc-900/40 border border-zinc-800/80 rounded-xl p-3.5 transition-all duration-200 hover:border-zinc-700">
                  <div className="flex justify-between items-start gap-3">
                    {activeHotel.thumbnail && (
                      <div className="flex-shrink-0 w-12 h-12 rounded-lg overflow-hidden border border-zinc-700/50">
                        <img src={activeHotel.thumbnail} alt={activeHotel.hotel_name} className="w-full h-full object-cover" />
                      </div>
                    )}
                    <div className="flex-grow space-y-0.5 pr-4">
                      <div className="text-zinc-200 font-sans font-semibold text-xs leading-normal">
                        {activeHotel.hotel_name}
                      </div>
                      <div className="flex items-center gap-2 text-[10px] font-medium">
                        <span className="text-zinc-500">Locked Choice</span>
                        {activeHotel.rating > 0 && (
                          <span className="flex items-center text-amber-400">
                            ★ {activeHotel.rating.toFixed(1)}
                          </span>
                        )}
                      </div>
                    </div>
                    <span className="text-sm font-mono font-bold text-white whitespace-nowrap">
                      {formatPrice(activeHotel.cost)}
                    </span>
                  </div>

                  {/* Hover Buttons Overlay */}
                  <div className="absolute inset-0 bg-zinc-950/95 backdrop-blur-[2px] flex items-center justify-center gap-3 opacity-0 group-hover:opacity-100 transition-opacity duration-200 rounded-xl">
                    <button
                      onClick={() => setShowHotelSwap(!showHotelSwap)}
                      className="bg-zinc-800 hover:bg-zinc-700 text-white font-semibold text-xs px-3.5 py-1.5 rounded-lg transition-all cursor-pointer"
                    >
                      {showHotelSwap ? "Close Swap" : "Swap"}
                    </button>
                    <a
                      href={getHotelLink(activeHotel)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="bg-amber-600 hover:bg-amber-500 text-white font-semibold text-xs px-3.5 py-1.5 rounded-lg transition-all flex items-center gap-1 cursor-pointer"
                    >
                      <span>Book</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                </div>

                {/* Dropdown Options for Hotel Swapping */}
                {showHotelSwap && hotelOptions.length > 0 && (
                  <div className="bg-zinc-900/30 border border-zinc-850 rounded-xl p-2.5 space-y-1.5 animate-fade-in">
                    <div className="text-[9px] text-zinc-500 font-bold uppercase tracking-wider px-1">Alternate accommodation choices:</div>
                    {hotelOptions.map((opt, i) => (
                      <label 
                        key={opt.id} 
                        className={`flex items-center justify-between p-2.5 rounded-lg border text-xs cursor-pointer transition-all duration-200 ${
                          selectedHotelIdx === i 
                            ? "bg-amber-600/10 border-amber-500 text-white" 
                            : "bg-zinc-900/40 border-zinc-800/50 text-zinc-400 hover:bg-zinc-800/30"
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <input
                            type="radio"
                            name="hotel_selection"
                            checked={selectedHotelIdx === i}
                            onChange={() => {
                              handleSwapItem("hotel", i);
                              setShowHotelSwap(false);
                            }}
                            className="accent-amber-500 cursor-pointer"
                          />
                          <span className="font-sans font-medium text-[11px] leading-tight">{opt.hotel_name}</span>
                        </div>
                        <span className="font-mono font-semibold text-[11px] whitespace-nowrap">{formatPrice(opt.cost)}</span>
                      </label>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Daily Schedule Itinerary */}
          {itinerary.length > 0 && (
            <div className="space-y-3 pt-2 border-t border-zinc-800/80">
              <div className="flex items-center gap-1 text-[10px] text-zinc-500 font-bold uppercase tracking-wider">
                <Calendar className="w-3.5 h-3.5" />
                <span>Curated Daily Itinerary</span>
              </div>
              <div className="space-y-3">
                {itinerary.map((day) => {
                  // Support both new `activities` array format and legacy morning/afternoon/evening
                  const activities: Array<{ time?: string; spot?: string; description?: string; estimated_spend?: number }> =
                    Array.isArray(day.activities) && day.activities.length > 0
                      ? day.activities
                      : [
                          day.morning   ? { time: "Morning",   description: day.morning   } : null,
                          day.afternoon ? { time: "Afternoon", description: day.afternoon } : null,
                          day.evening   ? { time: "Evening",   description: day.evening   } : null,
                        ].filter(Boolean) as any[];

                  const dailyTotal = activities.reduce(
                    (sum, a) => sum + (a.estimated_spend ?? 0),
                    day.estimated_cost ? 0 : 0  // reset; use activities if available
                  );
                  const showDailyTotal = dailyTotal > 0;
                  const displayCost = showDailyTotal ? dailyTotal : (day.estimated_cost ?? null);

                  return (
                    <details key={day.day} className="group bg-zinc-900/30 border border-zinc-850/60 rounded-xl [&_summary::-webkit-details-marker]:hidden">
                      <summary className="flex justify-between items-center cursor-pointer p-3.5 list-none select-none">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] bg-zinc-800 px-2 py-0.5 rounded text-zinc-300 font-semibold font-mono group-open:bg-amber-500/20 group-open:text-amber-400 transition-colors">
                            DAY {day.day}
                          </span>
                          <span className="text-zinc-200 font-sans font-semibold text-xs group-open:text-white transition-colors">{day.title}</span>
                        </div>
                        <div className="flex items-center gap-3">
                          {displayCost != null && (
                            <span className="text-[10px] text-amber-400/80 font-mono font-semibold">
                              ~{formatPrice(displayCost)}
                            </span>
                          )}
                          <span className="text-zinc-500 group-open:rotate-180 transition-transform duration-200">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>
                          </span>
                        </div>
                      </summary>

                      <div className="px-3.5 pb-3.5 space-y-1.5">
                        {activities.map((act, idx) => (
                          <div
                            key={idx}
                            className="flex gap-3 py-2 border-b border-zinc-800/40 last:border-0"
                          >
                            {/* Time column */}
                            <div className="flex-shrink-0 w-16 flex flex-col items-start gap-0.5 pt-0.5">
                              {act.time && (
                                <div className="flex items-center gap-1">
                                  <Clock className="w-2.5 h-2.5 text-zinc-600" />
                                  <span className="text-[9px] text-zinc-400 font-mono font-semibold">{act.time}</span>
                                </div>
                              )}
                              {act.estimated_spend != null && act.estimated_spend > 0 && (
                                <span className="text-[9px] text-amber-400/70 font-mono mt-0.5">
                                  {formatPrice(act.estimated_spend)}
                                </span>
                              )}
                            </div>

                            {/* Content column */}
                            <div className="flex-1 min-w-0">
                              {act.spot && (
                                <div className="flex items-center gap-1 mb-0.5">
                                  <MapPin className="w-2.5 h-2.5 text-blue-400/70 flex-shrink-0" />
                                  <span className="text-[10px] text-blue-300 font-semibold truncate">{act.spot}</span>
                                </div>
                              )}
                              {act.description && (
                                <p className="text-zinc-400 text-[10px] leading-relaxed font-medium font-sans">
                                  {act.description}
                                </p>
                              )}
                            </div>
                          </div>
                        ))}

                        {/* Daily tip (legacy field) */}
                        {day.tips && (
                          <div className="flex gap-2.5 mt-1 pt-2 border-t border-zinc-800/40">
                            <span className="text-[10px] text-emerald-400/60 font-bold uppercase tracking-wider min-w-[52px] mt-0.5">💡 Tip</span>
                            <p className="text-zinc-500 text-[10px] leading-relaxed font-medium font-sans italic">{day.tips}</p>
                          </div>
                        )}

                        {/* Daily total (only if activities supply individual costs) */}
                        {showDailyTotal && (
                          <div className="flex justify-between items-center mt-2 pt-2 border-t border-zinc-800/60">
                            <span className="text-[9px] text-zinc-500 font-bold uppercase tracking-wider">Daily Total</span>
                            <span className="text-[11px] text-amber-400 font-mono font-bold">{formatPrice(dailyTotal)}</span>
                          </div>
                        )}
                      </div>
                    </details>
                  );
                })}
              </div>
            </div>
          )}




        </div>
      )}

      {/* 5. Control Panel UI Overlay */}
      <ControlPanel
        onPlanTrip={handlePlanTrip}
        isLoading={isLoading}
        statusText={statusText}
        onReset={handleReset}
      />


      {/* Dynamic agent progress HUD — bottom-center, above input bar, progressive reveal */}
      {isLoading && (() => {
        // Only show steps that have actually started (in_progress, done, or failed)
        // pending steps are hidden until the server signals them
        const visibleSteps = Object.entries(planSteps).filter(
          ([, s]) => s.state !== "pending"
        );
        return (
          <div className="fixed bottom-[88px] left-1/2 -translate-x-1/2 z-[9998] w-80 bg-zinc-950/95 backdrop-blur-lg border border-zinc-800 rounded-2xl shadow-2xl overflow-hidden animate-fade-in pointer-events-none">
            {/* Header bar */}
            <div className="flex items-center gap-3 px-4 py-3 border-b border-zinc-800/80 bg-zinc-900/50">
              <div className="relative w-6 h-6 flex-shrink-0 flex items-center justify-center">
                <span className="absolute inset-0 border-2 border-blue-500/20 rounded-full" />
                <span className="absolute inset-0 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                <Sparkles className="w-3 h-3 text-blue-400" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-white font-semibold text-[11px] leading-none">Agent Planning Active</p>
                <p className="text-zinc-400 text-[9px] mt-0.5 truncate">{statusText || "Initializing..."}</p>
              </div>
            </div>

            {/* Progressive step log — only started steps */}
            {visibleSteps.length > 0 && (
              <div className="px-4 py-3 space-y-2.5">
                {visibleSteps.map(([stepKey, stepData]) => {
                  const isInProgress = stepData.state === "in_progress";
                  const isDone = stepData.state === "done";
                  const isFailed = stepData.state === "failed";

                  return (
                    <div key={stepKey} className="flex items-start gap-2.5 animate-fade-in">
                      {/* State icon */}
                      <div className="relative flex items-center justify-center w-4 h-4 flex-shrink-0 mt-0.5">
                        {isDone && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
                        {isInProgress && (
                          <>
                            <span className="absolute inset-0 border-[1.5px] border-blue-500/20 rounded-full" />
                            <span className="absolute inset-0 border-[1.5px] border-blue-500 border-t-transparent rounded-full animate-spin" />
                          </>
                        )}
                        {isFailed && (
                          <div className="w-4 h-4 rounded-full bg-red-500/20 flex items-center justify-center">
                            <span className="block w-2 h-0.5 bg-red-400 rotate-45 absolute" />
                            <span className="block w-2 h-0.5 bg-red-400 -rotate-45 absolute" />
                          </div>
                        )}
                      </div>

                      {/* Label + message */}
                      <div className="flex-1 min-w-0">
                        <span className={`block text-[11px] font-semibold leading-none mb-0.5 ${
                          isDone ? "text-emerald-400" :
                          isInProgress ? "text-blue-400" :
                          "text-red-400"
                        }`}>
                          {{ parsing: "Parsing Request", flights: "Searching Flights", budget: "Checking Budget", hotels: "Searching Hotels", itinerary: "Building Itinerary", finalize: "Finalizing" }[stepKey] ?? stepKey}
                        </span>
                        <span className="block text-[9px] text-zinc-500 leading-relaxed truncate">
                          {stepData.message}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Indeterminate progress bar */}
            <div className="h-[2px] bg-zinc-800 w-full overflow-hidden">
              <div className="h-full w-1/3 bg-blue-500 rounded-full animate-[slide_1.5s_ease-in-out_infinite]"
                style={{ animation: "slide 1.5s ease-in-out infinite" }} />
            </div>
          </div>
        );
      })()}

    </main>
  );
}
