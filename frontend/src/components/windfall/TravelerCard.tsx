"use client";

/**
 * TravelerCard — one abandoned cart in the browse list.
 *
 * Shows the PROVISIONAL estimate: the deterministic percentile tier and the
 * raw campaign share, both cheap and available before any inference. It is
 * labelled "Kemungkinan" precisely because it is not the Classifier's verdict,
 * which is reasoned and can differ.
 *
 * That labelling carries real weight. The estimate is what gives a reviewer a
 * hypothesis to test the model against; without it there is nothing to compare
 * the output to. And if estimate and verdict were always identical, the fair
 * question would be why a model is in the loop at all.
 *
 * The whole card is the click target. The button is labelled for the ACTION
 * ("Analisis"), never for an outcome -- "Recover" or "Rebuild" would pre-empt
 * the Classifier before it has run.
 */
import type { QueueEntry } from "@/lib/windfall/types";
import { abandonedLabel, dateRange, plainPct, stars } from "@/lib/windfall/format";

const TIER_TINT: Record<string, { bg: string; ink: string }> = {
  Value: { bg: "var(--wf-tier-value-bg)", ink: "var(--wf-tier-value-ink)" },
  Comfort: { bg: "var(--wf-tier-comfort-bg)", ink: "var(--wf-tier-comfort-ink)" },
  Premium: { bg: "var(--wf-tier-premium-bg)", ink: "var(--wf-tier-premium-ink)" },
  "Cold-start": { bg: "var(--wf-tier-cold-bg)", ink: "var(--wf-tier-cold-ink)" },
};

export function TravelerCard({
  entry,
  busy = false,
  onSelect,
}: {
  entry: QueueEntry;
  busy?: boolean;
  onSelect: (travelerId: string) => void;
}) {
  const tint = TIER_TINT[entry.tierEstimateLabel] ?? TIER_TINT["Cold-start"];
  const activate = () => {
    if (!busy) onSelect(entry.travelerId);
  };

  return (
    <article
      role="button"
      tabIndex={0}
      aria-label={`Analyse the abandoned cart for ${entry.name}`}
      aria-busy={busy}
      onClick={activate}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          activate();
        }
      }}
      style={{
        position: "relative",
        borderRadius: "var(--wf-radius-lg)",
        background: "var(--wf-white)",
        boxShadow: "var(--wf-ring-rule)",
        overflow: "hidden",
        boxSizing: "border-box",
        cursor: busy ? "wait" : "pointer",
        opacity: busy ? 0.6 : 1,
        transition: "box-shadow .12s ease, opacity .12s ease",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.boxShadow = "var(--wf-ring-ink)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.boxShadow = "var(--wf-ring-rule)";
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: 16,
          padding: "19px 19px 14px",
        }}
      >
        <div style={{ minWidth: 0, display: "flex", flexDirection: "column", gap: 8 }}>
          <h3 style={{ margin: 0, fontSize: 17, fontWeight: 700, letterSpacing: "-0.01em", color: "var(--wf-ink)" }}>
            {entry.name}
          </h3>

          {/* Provisional, and labelled as such. Not the Classifier's verdict. */}
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              alignSelf: "flex-start",
              padding: "4px 9px",
              borderRadius: "var(--wf-radius-sm)",
              background: tint.bg,
            }}
          >
            <span style={{ fontSize: 11.5, color: "var(--wf-ink-2)", opacity: 0.75 }}>
              Likely:
            </span>
            <span style={{ fontSize: 11.5, color: tint.ink }}>{entry.tierEstimateLabel}</span>
          </span>

          <span className="wf-mono" style={{ fontSize: 10.5, color: "var(--wf-ink-3)" }}>
            {entry.campaignShare === null
              ? "Campaign share — no history"
              : `Campaign share ${plainPct(entry.campaignShare)}`}
          </span>
        </div>

        <div style={{ textAlign: "right", flexShrink: 0 }}>
          <div className="wf-eyebrow">Abandoned</div>
          <div className="wf-mono" style={{ marginTop: 4, fontSize: 13, color: "var(--wf-ink)", whiteSpace: "nowrap" }}>
            {abandonedLabel(entry.abandonedHoursAgo)}
          </div>
          <div className="wf-mono" style={{ marginTop: 6, fontSize: 11, color: "var(--wf-ink-3)" }}>
            {entry.bookings === 0 ? "no bookings" : `${entry.bookings} bookings`}
          </div>
        </div>
      </div>

      {/* Cart contents sit in a dashed box, per the design system. */}
      <div style={{ padding: "0 19px" }}>
        <div
          style={{
            padding: "12px 14px",
            border: "1px dashed var(--wf-rule)",
            borderRadius: 2,
            display: "flex",
            flexDirection: "column",
            gap: 6,
          }}
        >
          <div className="wf-mono" style={{ fontSize: 13, color: "var(--wf-ink)" }}>
            {entry.route} <span style={{ color: "var(--wf-ink-2)" }}>{entry.carrier}</span>
          </div>
          <div style={{ fontSize: 12.5, color: "var(--wf-ink-2)" }}>
            {entry.hotelName}{" "}
            <span className="wf-mono" style={{ color: "var(--wf-ink-3)" }}>
              {stars(entry.hotelStars)}
            </span>
          </div>
          <div className="wf-mono" style={{ fontSize: 11, color: "var(--wf-ink-3)" }}>
            {dateRange(entry.departDate, entry.returnDate)} &middot; {entry.passengers} pax &middot;{" "}
            {entry.cabin}
          </div>
        </div>
      </div>

      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 16,
          padding: "14px 19px 16px",
        }}
      >
        <span className="wf-mono" style={{ fontSize: 11, color: "var(--wf-ink-3)" }}>
          {entry.hotelCity}
        </span>
        <span
          aria-hidden
          style={{
            flex: "0 0 auto",
            minWidth: 96,
            padding: "9px 16px",
            fontSize: 13,
            fontWeight: 700,
            textAlign: "center",
            borderRadius: 5,
            background: "var(--wf-ink)",
            color: "var(--wf-paper)",
          }}
        >
          {busy ? "Running…" : "Analisis"}
        </span>
      </div>
    </article>
  );
}
