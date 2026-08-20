"use client";

/**
 * HoldPanel — whether the fare is actually frozen, stated plainly.
 *
 * Paper section 2.1 promises that any deadline shown to a traveler is real.
 * Keeping that promise means the NEGATIVE case has to be renderable: a cart
 * with no guarantee must visibly say so, not merely omit a countdown and leave
 * the analyst to infer it.
 *
 * Three states, and the middle one is the one that matters:
 *
 *   eligible      real expiry from Duffel payment_required_by
 *   not eligible  no deadline at all — not shorter, not softened, none
 *   simulated     pre-authorization fallback, labelled as simulated
 *
 * The scope line is not a footnote. Duffel holds a FLIGHT offer; hotels have
 * no equivalent primitive and re-price at conversion. Saying "your trip is
 * frozen" when only half of it is would be the kind of small dishonesty this
 * product is meant to avoid.
 */
import type { HoldStatus } from "@/lib/windfall/types";

const STATE_LABEL: Record<string, string> = {
  eligible: "Fare guaranteed",
  not_eligible: "No guarantee",
  simulated: "Simulated hold",
};

export function HoldPanel({ hold }: { hold: HoldStatus }) {
  const eligible = hold.state === "eligible";
  const simulated = hold.state === "simulated";

  const ink = eligible
    ? "var(--wf-signal-ink)"
    : simulated
      ? "var(--wf-amber)"
      : "var(--wf-ink-3)";
  const bg = eligible
    ? "var(--wf-signal-tint)"
    : simulated
      ? "var(--wf-amber-tint)"
      : "var(--wf-surface)";

  return (
    <section
      aria-label="Price freeze eligibility"
      style={{
        borderRadius: "var(--wf-radius-md)",
        background: "var(--wf-white)",
        boxShadow: "var(--wf-ring-border)",
        overflow: "hidden",
      }}
    >
      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
          padding: "10px 16px",
          background: bg,
          borderBottom: "1px solid var(--wf-rule)",
        }}
      >
        <span className="wf-eyebrow" style={{ color: ink }}>
          Price freeze &middot; {hold.carrier ?? "carrier"}
        </span>
        <span
          className="wf-mono"
          style={{ fontSize: 11, letterSpacing: "0.06em", textTransform: "uppercase", color: ink }}
        >
          {STATE_LABEL[hold.state] ?? hold.state}
        </span>
      </header>

      <div style={{ padding: "13px 16px", display: "flex", flexDirection: "column", gap: 8 }}>
        {eligible && hold.expiresAt ? (
          <div className="wf-mono" style={{ fontSize: 13, color: "var(--wf-ink)" }}>
            Held until {hold.expiresAt}
          </div>
        ) : (
          /* Deliberately no time, no countdown, no "book soon". An absent
             guarantee reads as absence. */
          <div style={{ fontSize: 13, color: "var(--wf-ink-2)" }}>
            {simulated
              ? "Pre-authorization fallback, simulated for this stage. Not an airline guarantee."
              : "This carrier requires instant payment, so no deadline is shown."}
          </div>
        )}

        {hold.note && (
          <p style={{ margin: 0, fontSize: 12.5, lineHeight: 1.6, color: "var(--wf-ink-2)" }}>
            {hold.note}
          </p>
        )}

        <p className="wf-mono" style={{ margin: 0, fontSize: 10.5, color: "var(--wf-ink-3)" }}>
          Scope: flight only &mdash; the hotel re-prices at conversion.
        </p>
      </div>
    </section>
  );
}
