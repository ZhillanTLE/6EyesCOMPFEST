/**
 * Contract mirror for the recovery pipeline.
 *
 * camelCase on the wire, matching the data contract in CLAUDE.md. The backend
 * keeps snake_case Python internally and converts once at the JSON boundary
 * (backend/recovery/serialize.py).
 *
 * backend/recovery/seed/golden.json is the shared reference both sides build
 * against; `npm run build` typechecking against it is what catches drift.
 */

export const OUTCOMES = ["rebuild", "lateral", "reminder", "alternative", "error"] as const;
export type Outcome = (typeof OUTCOMES)[number];

/** Outcomes that put a changed cart in front of the traveler. */
export const INTERVENING_OUTCOMES: readonly Outcome[] = ["rebuild", "lateral", "alternative"];

export type Tier = "Value" | "Comfort" | "Premium";
export type HoldState = "eligible" | "not_eligible" | "simulated";
export type StageName = "classifier" | "searcher" | "notifier";

export interface HotelSpec {
  name: string;
  stars: number;
  city: string;
  area: string;
  checkIn: string;
  checkOut: string;
  priceIdr: number;
}

export interface FlightSpec {
  carrier: string;
  origin: string;
  destination: string;
  departDate: string;
  returnDate: string | null;
  cabin: string;
  passengers: number;
  priceIdr: number;
  duffelOfferId: string | null;
}

export interface Classification {
  tier: Tier;
  tierPrior: Tier;
  /** tau(tier): 0.05 | 0.10 | 0.15 */
  threshold: number;
  reasoning: string[];
  overrideReason: string | null;
  isColdStart: boolean;
  /** "history" | "cart_proxy" — cart_proxy must be labelled as such in the UI. */
  tierSource: string;
}

export interface GateResult {
  opened: boolean;
  /** null when the traveler has no history: unmeasurable, never fabricated. */
  campaignShare: number | null;
  budgetGap: number;
  priceSensitive: boolean | null;
  overBudget: boolean;
  reason: string;
  coldStartException: boolean;
}

export interface LadderAttempt {
  index: number;
  rung: string;
  label: string;
  /** false = nothing found. Distinct from priced-but-missed (available, !cleared). */
  available: boolean;
  totalIdr: number | null;
  delta: number | null;
  cleared: boolean;
  hotel: HotelSpec | null;
  note: string | null;
}

export interface Decision {
  outcome: Outcome;
  clearedRung: string | null;
  attempts: LadderAttempt[];
  finalTotalIdr: number | null;
  /** What the traveler saves. NOT what the partner gave up. */
  savingIdr: number;
  savingPct: number | null;
  /** What the partner conceded. Zero on every path, by construction. */
  marginConcededIdr: number;
  rationale: string;
}

export interface HoldStatus {
  state: HoldState;
  /** From Duffel payment_required_by. The only legitimate countdown source. */
  expiresAt: string | null;
  carrier: string | null;
  note: string | null;
}

export interface StageTiming {
  stage: StageName;
  durationMs: number;
}

export interface NotificationDraft {
  subject: string;
  bodyParagraphs: string[];
  whatsapp: string;
  ctaLabel: string;
  channelNote: string | null;
}

export interface RecoveryResult {
  cartId: string;
  travelerName: string;
  classification: Classification;
  gate: GateResult;
  decision: Decision;
  hold: HoldStatus;
  notification: NotificationDraft | null;
  timings: StageTiming[];
  originalTotalIdr: number;
  /** "live" | "fixture" — fixture must be visibly labelled in the UI. */
  source: string;
}

/**
 * Browse-list entry.
 *
 * Carries `tierEstimate` and `campaignShare`: the cheap deterministic estimate,
 * available before any inference. It is NOT the Classifier's verdict, and the
 * UI must label it provisional so the difference is legible — if the estimate
 * and the reasoned verdict were always identical, the fair question would be
 * why a model is in the loop at all.
 */
export interface QueueEntry {
  travelerId: string;
  cartId: string;
  name: string;
  bookings: number;
  tierEstimate: Tier;
  /** "Cold-start" when derived from the cart rather than from history. */
  tierEstimateLabel: string;
  isColdStart: boolean;
  campaignShare: number | null;
  route: string;
  carrier: string;
  cabin: string;
  passengers: number;
  departDate: string;
  returnDate: string | null;
  hotelName: string;
  hotelStars: number;
  hotelCity: string;
  checkIn: string;
  checkOut: string;
  abandonedHoursAgo: number;
}

export interface QueueResponse {
  queue: QueueEntry[];
  source: string;
}

/** A deadline may render only when a carrier genuinely guaranteed the fare. */
export function mayRenderDeadline(hold: HoldStatus): boolean {
  return hold.state === "eligible" && Boolean(hold.expiresAt);
}
