# Next.js Component Structure & Layout

This document outlines the visual structure and hierarchical separation of the Next.js layout components. 

## Component Tree

```
frontend/
├── src/
│   ├── app/
│   │   ├── page.tsx               # Main page layout & WebSocket state manager
│   │   └── globals.css            # Tailwind & overall styling variables
│   └── components/
│       ├── MapCanvas.tsx          # Mapbox GL JS 3D Globe canvas wrapper
│       ├── BudgetTracker.tsx      # Floating budget metrics HUD overlay
│       └── ControlPanel.tsx       # Prompt entry & simulation control HUD overlay
└── public/
    └── mock_socket_injector.js    # Client-side SocketIO event injector
```

## Architectural Separation of Concerns

To prevent visual stuttering and rendering lag during real-time WebSocket state updates, the layout keeps the **Map canvas rendering** strictly isolated from the **DOM-based UI overlays**:

### 1. Viewport Canvas (`MapCanvas.tsx`)
- Renders full-screen at `z-index: 0`.
- Holds the single Mapbox GL instance context.
- Interacts with map geometries (Turf geodesic arc routes) and manages the initialization/destruction of custom SVG airport/hotel pin markers.
- Updates via direct map instance commands (`flyTo`, `fitBounds`, source data updates) instead of triggering React parent re-renders.

### 2. State & WebSocket Controller (`page.tsx`)
- Renders as the parent container.
- Connects to the backend server WebSocket port.
- Maintains React state for trip budget, active flights, and hotel bookings.
- Dispatches state updates down to overlays and the Map canvas.

### 3. Floating HUD Overlays (`BudgetTracker.tsx`, `ControlPanel.tsx`)
- Renders floating absolute elements at high `z-index` levels (`z-index: 10`).
- Standardized typography and monospace numbers for immediate budget readability.
- Uses smooth CSS transitions on state changes to animate countdown figures.
