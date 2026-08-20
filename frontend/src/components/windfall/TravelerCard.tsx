/**
 * TravelerCard — one abandoned cart in the browse list.
 *
 * Shows booking history and the cart's contents. It deliberately does NOT show
 * the tier or the campaign share: those are the Classifier's conclusions, and
 * printing them on the card the analyst is about to click would let the
 * pipeline appear to conclude something already on screen. The prototype did
 * exactly that, with a "Likelihood: Value" chip and a campaign-share line on
 * every card before anything had run.
 *
 * Selection is an inset ink ring plus a left ink bar, never a fill.
 */
import type { QueueEntry } from "@/lib/windfall/types";
import { abandonedLabel, dateRange, stars } from "@/lib/windfall/format";

export function TravelerCard({
  entry,
  selected = false,
  busy = false,
  onSelect,
}: {
  entry: QueueEntry;
  selected?: boolean;
  busy?: boolean;
  onSelect: (travelerId: string) => void;
}) {
  const coldStart = entry.booking_count <= 1;

  return (
    <article
      style={{
        position: "relative",
        borderRadius: "var(--wf-radius-lg)",
        background: "var(--wf-white)",
        boxShadow: selected ? "var(--wf-ring-ink)" : "var(--wf-ring-rule)",
        overflow: "hidden",
        boxSizing: "border-box",
        transition: "box-shadow .12s ease",
      }}
    >
      {selected && (
        <span
          aria-hidden
          style={{
            position: "absolute",
            left: 0,
            top: 15,
            bottom: 15,
            width: 3,
            borderRadius: "0 2px 2px 0",
            background: "var(--wf-ink)",
          }}
        />
      )}

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: 16,
          padding: "19px 19px 14px",
        }}
      >
        <div style={{ minWidth: 0 }}>
          <h3 style={{ margin: 0, fontSize: 17, fontWeight: 700, letterSpacing: "-0.01em", color: "var(--wf-ink)" }}>
            {entry.name}
          </h3>
          <p className="wf-mono" style={{ margin: "6px 0 0", fontSize: 11, color: "var(--wf-ink-3)" }}>
            {coldStart
              ? "Belum ada riwayat pemesanan"
              : `${entry.booking_count} pemesanan sebelumnya`}
          </p>
        </div>
        <div style={{ textAlign: "right", flexShrink: 0 }}>
          <div className="wf-eyebrow">Ditinggalkan</div>
          <div className="wf-mono" style={{ marginTop: 4, fontSize: 13, color: "var(--wf-ink)", whiteSpace: "nowrap" }}>
            {abandonedLabel(entry.abandoned_hours_ago)}
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
            {entry.route}{" "}
            <span style={{ color: "var(--wf-ink-2)" }}>{entry.carrier}</span>
          </div>
          <div style={{ fontSize: 12.5, color: "var(--wf-ink-2)" }}>
            {entry.hotel_name}{" "}
            <span className="wf-mono" style={{ color: "var(--wf-ink-3)" }}>
              {stars(entry.hotel_stars)}
            </span>
          </div>
          <div className="wf-mono" style={{ fontSize: 11, color: "var(--wf-ink-3)" }}>
            {dateRange(entry.depart_date, entry.return_date)} &middot; {entry.passengers} pax &middot;{" "}
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
          {entry.hotel_city}
        </span>
        <button
          type="button"
          disabled={busy}
          onClick={() => onSelect(entry.traveler_id)}
          aria-label={`Jalankan pemulihan untuk ${entry.name}`}
          style={{
            flex: "0 0 auto",
            minWidth: 96,
            padding: "9px 16px",
            fontSize: 13,
            fontWeight: 700,
            border: "none",
            borderRadius: 5,
            background: "var(--wf-ink)",
            color: "var(--wf-paper)",
            cursor: busy ? "wait" : "pointer",
            opacity: busy ? 0.5 : 1,
            transition: "opacity .12s ease",
          }}
        >
          {busy ? "Menjalankan…" : "Recover"}
        </button>
      </div>
    </article>
  );
}
