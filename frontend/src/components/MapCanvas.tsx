import React, { useEffect, useRef, useState } from "react";
import { setOptions, importLibrary } from "@googlemaps/js-api-loader";

interface MapCanvasProps {
  googleMapsApiKey: string;
  outboundFlight: {
    carrier: string;
    origin: [number, number]; // [lng, lat]
    destination: [number, number]; // [lng, lat]
    cost: number;
  } | null;
  inboundFlight: {
    carrier: string;
    origin: [number, number]; // [lng, lat]
    destination: [number, number]; // [lng, lat]
    cost: number;
  } | null;
  hotelData: {
    hotel_name: string;
    location: [number, number]; // [lng, lat]
    cost: number;
    reasoning?: string;
  } | null;
  itinerary?: any[];
  currentStep?: string;
}

const darkMapStyle = [
  { elementType: "geometry", stylers: [{ color: "#0f0f12" }] },
  { elementType: "labels.text.stroke", stylers: [{ color: "#0f0f12" }, { weight: 3 }] },
  { elementType: "labels.text.fill", stylers: [{ color: "#5c5c64" }] },
  {
    featureType: "administrative.locality",
    elementType: "labels.text.fill",
    stylers: [{ color: "#a0a0a8" }]
  },
  {
    featureType: "poi",
    elementType: "labels.text.fill",
    stylers: [{ color: "#4b4b54" }]
  },
  {
    featureType: "poi.park",
    elementType: "geometry",
    stylers: [{ color: "#131317" }]
  },
  {
    featureType: "road",
    elementType: "geometry",
    stylers: [{ color: "#1c1c22" }]
  },
  {
    featureType: "road",
    elementType: "geometry.stroke",
    stylers: [{ color: "#131317" }]
  },
  {
    featureType: "road",
    elementType: "labels.text.fill",
    stylers: [{ color: "#6b6b76" }]
  },
  {
    featureType: "transit",
    elementType: "geometry",
    stylers: [{ color: "#1c1c22" }]
  },
  {
    featureType: "water",
    elementType: "geometry",
    stylers: [{ color: "#050507" }]
  }
];

export default function MapCanvas({ googleMapsApiKey, outboundFlight, inboundFlight, hotelData, itinerary, currentStep }: MapCanvasProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<google.maps.Map | null>(null);
  
  // Keep track of map entities for dynamic clearing
  const markersRef = useRef<{ [key: string]: google.maps.Marker | null }>({
    origin: null,
    destination: null,
    hotel: null
  });

  const polylinesRef = useRef<{ [key: string]: google.maps.Polyline | null }>({
    outbound: null,
    inbound: null,
    hotelLink: null
  });

  const [mapLoaded, setMapLoaded] = useState(false);

  // Initialize Google Map
  useEffect(() => {
    if (!mapContainerRef.current) return;

    const apiKey = googleMapsApiKey || process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || "";
    console.log("Initializing Google Maps API. Key present:", !!apiKey);

    setOptions({
      key: apiKey,
      libraries: ["geometry"]
    });

    Promise.all([
      importLibrary("maps"),
      importLibrary("marker")
    ]).then(([mapsLib]) => {
      if (!mapContainerRef.current) return;

      const map = new mapsLib.Map(mapContainerRef.current, {
        center: { lat: 25, lng: -40 },
        zoom: 2.2,
        styles: darkMapStyle,
        disableDefaultUI: true,
        zoomControl: false,
        backgroundColor: "#050507"
      });

      mapRef.current = map;
      setMapLoaded(true);
    }).catch(err => {
      console.error("Failed to load Google Maps SDK:", err);
    });

    return () => {
      clearAllOverlays();
      mapRef.current = null;
    };
  }, [googleMapsApiKey]);

  const clearAllOverlays = () => {
    Object.keys(markersRef.current).forEach(key => {
      markersRef.current[key]?.setMap(null);
      markersRef.current[key] = null;
    });
    Object.keys(polylinesRef.current).forEach(key => {
      polylinesRef.current[key]?.setMap(null);
      polylinesRef.current[key] = null;
    });
  };

  // Render Flights (Outbound and Inbound)
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapLoaded) return;

    // Clear old flights polylines and airport markers
    if (polylinesRef.current.outbound) {
      polylinesRef.current.outbound.setMap(null);
      polylinesRef.current.outbound = null;
    }
    if (polylinesRef.current.inbound) {
      polylinesRef.current.inbound.setMap(null);
      polylinesRef.current.inbound = null;
    }
    if (markersRef.current.origin) {
      markersRef.current.origin.setMap(null);
      markersRef.current.origin = null;
    }
    if (markersRef.current.destination) {
      markersRef.current.destination.setMap(null);
      markersRef.current.destination = null;
    }

    if (!outboundFlight) return;

    const { origin, destination } = outboundFlight;
    const originLatLng = { lat: origin[1], lng: origin[0] };
    const destLatLng = { lat: destination[1], lng: destination[0] };

    // Pin SVGs
    const originPinSvg = `
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="32" height="32" fill="none" stroke="#10b981" stroke-width="2">
        <circle cx="12" cy="12" r="10" fill="rgba(16, 185, 129, 0.15)"/>
        <path stroke-linecap="round" stroke-linejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
      </svg>
    `;

    const destPinSvg = `
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="32" height="32" fill="none" stroke="#3b82f6" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" />
        <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z" />
      </svg>
    `;

    // Drop Departure Airport Marker
    const originMarker = new google.maps.Marker({
      position: originLatLng,
      map: map,
      icon: {
        url: "data:image/svg+xml;charset=UTF-8," + encodeURIComponent(originPinSvg),
        anchor: new google.maps.Point(16, 16)
      },
      title: "Departure Airport (SFO)"
    });
    markersRef.current.origin = originMarker;

    const originInfo = new google.maps.InfoWindow({
      content: "<div class='text-zinc-950 font-sans p-1 font-bold'>San Francisco Int'l Airport (SFO)</div>"
    });
    originMarker.addListener("click", () => originInfo.open(map, originMarker));

    // Drop Destination Airport Marker
    const destMarker = new google.maps.Marker({
      position: destLatLng,
      map: map,
      icon: {
        url: "data:image/svg+xml;charset=UTF-8," + encodeURIComponent(destPinSvg),
        anchor: new google.maps.Point(16, 16)
      },
      title: "Destination Airport"
    });
    markersRef.current.destination = destMarker;

    const destInfo = new google.maps.InfoWindow({
      content: `<div class='text-zinc-950 font-sans p-1'><div class='font-bold'>Destination Airport</div><div class='text-xs text-zinc-500'>Flight Locked</div></div>`
    });
    destMarker.addListener("click", () => destInfo.open(map, destMarker));

    // We no longer draw disparate flights and hotels here.
    // We will draw one sequential path encompassing origin -> dest -> hotel -> spots -> hotel -> dest -> origin
  }, [outboundFlight, inboundFlight, mapLoaded]);

  // Handle Full Connected Route Drawing
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapLoaded || !outboundFlight) return;

    // Clear old markers and polylines for the full route (we will use new keys in polylinesRef/markersRef)
    Object.keys(markersRef.current).forEach(k => {
      if(k !== 'origin' && k !== 'destination') {
        markersRef.current[k]?.setMap(null);
      }
    });
    Object.keys(polylinesRef.current).forEach(k => {
      polylinesRef.current[k]?.setMap(null);
    });

    const routePath: google.maps.LatLngLiteral[] = [];
    const bounds = new google.maps.LatLngBounds();

    const originLatLng = { lat: outboundFlight.origin[1], lng: outboundFlight.origin[0] };
    const destLatLng = { lat: outboundFlight.destination[1], lng: outboundFlight.destination[0] };
    
    routePath.push(originLatLng);
    bounds.extend(originLatLng);
    
    routePath.push(destLatLng);
    bounds.extend(destLatLng);
    
    // Draw Flight Segment (Blue)
    const flightOut = new google.maps.Polyline({
      path: [originLatLng, destLatLng],
      geodesic: true,
      strokeColor: "#60a5fa",
      strokeOpacity: 0.8,
      strokeWeight: 3
    });
    flightOut.setMap(map);
    polylinesRef.current.flightOut = flightOut;

    let hotelLatLng: google.maps.LatLngLiteral | null = null;
    
    if (hotelData) {
      hotelLatLng = { lat: hotelData.location[1], lng: hotelData.location[0] };
      
      const hotelPinSvg = `
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="32" height="32" fill="none" stroke="#f59e0b" stroke-width="2">
          <circle cx="12" cy="12" r="10" fill="rgba(245, 158, 11, 0.15)"/>
          <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 21v-4.875c0-.621.504-1.125 1.125-1.125h5.25c.621 0 1.125.504 1.125 1.125V21m0 0h4.5V3.545M12.75 7.5v.008H12.75V7.5zm0 2.25v.008H12.75V9.75zm0 2.25v.008H12.75v-.008zm-3.375-4.5h.008v.008H9.375V7.5zm0 2.25h.008v.008H9.375V9.75zm0 2.25h.008v.008H9.375v-.008zm6.75-4.5h.008v.008h-.008V7.5zm0 2.25h.008v.008h-.008V9.75zm0 2.25h.008v.008h-.008v-.008zm2.25-4.5h.008v.008H18.38V7.5zm0 2.25h.008v.008H18.38V9.75z" />
        </svg>
      `;

      const hotelMarker = new google.maps.Marker({
        position: hotelLatLng,
        map: map,
        icon: {
          url: "data:image/svg+xml;charset=UTF-8," + encodeURIComponent(hotelPinSvg),
          anchor: new google.maps.Point(16, 16)
        },
        title: hotelData.hotel_name
      });
      markersRef.current.hotel = hotelMarker;
      
      const hotelInfo = new google.maps.InfoWindow({
        content: `<div class='text-zinc-950 font-sans p-1'><div class='font-bold'>${hotelData.hotel_name}</div><div class='text-xs text-zinc-500'>${hotelData.reasoning || "Selected Hotel"}</div></div>`
      });
      hotelMarker.addListener("click", () => hotelInfo.open(map, hotelMarker));
      
      routePath.push(hotelLatLng);
      bounds.extend(hotelLatLng);
    }

    const groundPath = [];
    if (hotelLatLng) groundPath.push(destLatLng, hotelLatLng);

    if (itinerary && itinerary.length > 0) {
      let spotIdx = 0;
      itinerary.forEach(day => {
        if (day.spots) {
          day.spots.forEach((spot: any) => {
            const spotLatLng = { lat: spot.lat, lng: spot.lng };
            groundPath.push(spotLatLng);
            bounds.extend(spotLatLng);
            
            const spotMarker = new google.maps.Marker({
              position: spotLatLng,
              map: map,
              icon: {
                path: google.maps.SymbolPath.CIRCLE,
                scale: 6,
                fillColor: "#ef4444",
                fillOpacity: 1,
                strokeWeight: 2,
                strokeColor: "#ffffff"
              },
              title: spot.name
            });
            markersRef.current[`spot_${spotIdx}`] = spotMarker;
            
            const spotInfo = new google.maps.InfoWindow({
              content: `<div class='text-zinc-950 font-sans p-1'><b>${spot.name}</b><br/><span class='text-xs text-zinc-500'>${spot.time}</span></div>`
            });
            spotMarker.addListener("click", () => spotInfo.open(map, spotMarker));
            spotIdx++;
          });
        }
      });
    }

    if (hotelLatLng) groundPath.push(hotelLatLng);
    groundPath.push(destLatLng);

    // Draw Ground Path (Dashed Orange)
    if (groundPath.length > 1) {
      const groundLine = new google.maps.Polyline({
        path: groundPath,
        strokeColor: "#f59e0b",
        strokeOpacity: 0,
        strokeWeight: 2.5,
        icons: [{
          icon: { path: "M 0,-1 0,1", strokeOpacity: 1, scale: 2 },
          offset: "0",
          repeat: "10px"
        }]
      });
      groundLine.setMap(map);
      polylinesRef.current.groundLine = groundLine;
    }

    if (inboundFlight) {
      const inboundPath = new google.maps.Polyline({
        path: [destLatLng, originLatLng],
        geodesic: true,
        strokeColor: "#c084fc", // Purple/pink
        strokeOpacity: 0.7,
        strokeWeight: 2.5,
        icons: [{
          icon: {
            path: google.maps.SymbolPath.FORWARD_CLOSED_ARROW,
            strokeColor: "#c084fc",
            fillColor: "#c084fc",
            fillOpacity: 1,
            scale: 2
          },
          offset: "50%"
        }]
      });
      inboundPath.setMap(map);
      polylinesRef.current.flightIn = inboundPath;
    }

    // We remove the automatic map.fitBounds here, because we handle camera animation in a separate useEffect
    // based on currentStep.

  }, [hotelData, outboundFlight, inboundFlight, mapLoaded, itinerary]);

  // Handle Camera Choreography (FR1)
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapLoaded) return;

    // A helper to smoothly fly to bounds (zoom out slightly, pan, then fit bounds)
    const flyToBounds = (bounds: google.maps.LatLngBounds, padding: number = 50) => {
      const currentZoom = map.getZoom() || 2;
      const targetCenter = bounds.getCenter();
      
      // We'll do a simple smooth panTo (which Google Maps natively animates)
      map.panTo(targetCenter);
      
      // And we use a setTimeout to let it pan before applying the final bounds for zoom
      setTimeout(() => {
        map.fitBounds(bounds, padding);
      }, 800); // Wait 800ms for pan to finish
    };

    if (currentStep === "parsing") {
      // Gentle zoom to origin or just no move
    } else if (currentStep === "flights" && outboundFlight) {
      const originLatLng = { lat: outboundFlight.origin[1], lng: outboundFlight.origin[0] };
      const destLatLng = { lat: outboundFlight.destination[1], lng: outboundFlight.destination[0] };
      const bounds = new google.maps.LatLngBounds();
      bounds.extend(originLatLng);
      bounds.extend(destLatLng);
      flyToBounds(bounds, 100);
    } else if (currentStep === "hotels" && hotelData && outboundFlight) {
      const destLatLng = { lat: outboundFlight.destination[1], lng: outboundFlight.destination[0] };
      const hotelLatLng = { lat: hotelData.location[1], lng: hotelData.location[0] };
      const bounds = new google.maps.LatLngBounds();
      bounds.extend(destLatLng);
      bounds.extend(hotelLatLng);
      flyToBounds(bounds, 80);
    } else if (currentStep === "itinerary" && itinerary && itinerary.length > 0) {
      // Fly to the most recently added day's spots
      const latestDay = itinerary[itinerary.length - 1];
      if (latestDay.spots && latestDay.spots.length > 0) {
        const bounds = new google.maps.LatLngBounds();
        latestDay.spots.forEach((spot: any) => {
          bounds.extend({ lat: spot.lat, lng: spot.lng });
        });
        flyToBounds(bounds, 60);
      }
    } else if (currentStep === "finalize" && outboundFlight) {
      // Zoom out to fit full trip
      const bounds = new google.maps.LatLngBounds();
      const originLatLng = { lat: outboundFlight.origin[1], lng: outboundFlight.origin[0] };
      bounds.extend(originLatLng);
      
      if (hotelData) {
        bounds.extend({ lat: hotelData.location[1], lng: hotelData.location[0] });
      }
      if (itinerary) {
        itinerary.forEach(day => {
          if (day.spots) {
            day.spots.forEach((spot: any) => {
              bounds.extend({ lat: spot.lat, lng: spot.lng });
            });
          }
        });
      }
      flyToBounds(bounds, 120);
    }
  }, [currentStep, mapLoaded, outboundFlight, hotelData, itinerary]);

  return (
    <div className="relative w-full h-full">
      <div ref={mapContainerRef} className="absolute inset-0 w-full h-full bg-[#050507]" />
      {!mapLoaded && (
        <div className="absolute inset-0 flex items-center justify-center bg-zinc-950/80 z-20">
          <div className="text-zinc-400 text-sm flex flex-col items-center gap-3">
            <span className="w-6 h-6 border-2 border-zinc-700 border-t-blue-500 rounded-full animate-spin" />
            <span>Loading Google Maps Canvas...</span>
          </div>
        </div>
      )}
    </div>
  );
}
