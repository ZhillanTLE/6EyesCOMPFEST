/**
 * Contract mirror for the recovery pipeline.
 *
 * Hand-kept in step with backend/recovery/schemas.py. The golden fixture at
 * backend/recovery/seed/golden.json is the shared reference both sides build
 * against, and `npm run typecheck` against it is what catches drift.
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
  check_in: string;
  check_out: string;
  price_idr: number;
}

export interface FlightSpec {
  carrier: string;
  origin: string;
  destination: string;
  depart_date: string;
  return_date: string | null;
  cabin: string;
  passengers: number;
  price_idr: number;
  duffel_offer_id: string | null;
}

export interface Classification {
  tier: Tier;
  tier_prior: Tier;
  /** tau(tier): 0.05 | 0.10 | 0.15 */
  threshold: number;
  reasoning: string[];
  override_reason: string | null;
  is_cold_start: boolean;
  /** "history" | "cart_proxy" — cart_proxy must be labelled as such in the UI. */
  tier_source: string;
}

export interface GateResult {
  opened: boolean;
  /** null when the traveler has no history: unmeasurable, never fabricated. */
  campaign_share: number | null;
  budget_gap: number;
  price_sensitive: boolean | null;
  over_budget: boolean;
  reason: string;
  cold_start_exception: boolean;
}

export interface LadderAttempt {
  index: number;
  rung: string;
  label: string;
  /** false = nothing found. Distinct from priced-but-missed (available, !cleared). */
  available: boolean;
  total_idr: number | null;
  delta: number | null;
  cleared: boolean;
  hotel: HotelSpec | null;
  note: string | null;
}

export interface Decision {
  outcome: Outcome;
  cleared_rung: string | null;
  attempts: LadderAttempt[];
  final_total_idr: number | null;
  /** What the traveler saves. NOT what the partner gave up — see below. */
  saving_idr: number;
  saving_pct: number | null;
  /** What the partner conceded. Zero on every path, by construction. */
  margin_conceded_idr: number;
  rationale: string;
}

export interface HoldStatus {
  state: HoldState;
  /** Sourced from Duffel payment_required_by. The only legitimate countdown. */
  expires_at: string | null;
  carrier: string | null;
  note: string | null;
}

export interface StageTiming {
  stage: StageName;
  duration_ms: number;
}

export interface NotificationDraft {
  subject: string;
  body_paragraphs: string[];
  whatsapp: string;
  cta_label: string;
  channel_note: string | null;
}

export interface RecoveryResult {
  cart_id: string;
  traveler_name: string;
  classification: Classification;
  gate: GateResult;
  decision: Decision;
  hold: HoldStatus;
  notification: NotificationDraft | null;
  timings: StageTiming[];
  original_total_idr: number;
  /** "live" | "fixture" — fixture must be visibly labelled in the UI. */
  source: string;
}

/**
 * Browse-list entry. Deliberately carries neither tier nor campaign share:
 * those are the Classifier's conclusions, and showing them before the pipeline
 * runs would let it appear to conclude what was already on the card.
 */
export interface QueueEntry {
  traveler_id: string;
  cart_id: string;
  name: string;
  booking_count: number;
  route: string;
  carrier: string;
  cabin: string;
  passengers: number;
  depart_date: string;
  return_date: string | null;
  hotel_name: string;
  hotel_stars: number;
  hotel_city: string;
  check_in: string;
  check_out: string;
  abandoned_hours_ago: number;
}

export interface QueueResponse {
  queue: QueueEntry[];
  source: string;
}

/** A deadline may render only when a carrier genuinely guaranteed the fare. */
export function mayRenderDeadline(hold: HoldStatus): boolean {
  return hold.state === "eligible" && Boolean(hold.expires_at);
}
