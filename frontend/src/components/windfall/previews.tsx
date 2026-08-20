/**
 * Notification previews.
 *
 * The signature tension the design system asks for: the reasoning timeline
 * reads as system output (mono, timings, arrow bullets), while these read as a
 * real message a person received (sans, natural sentences, real mail and chat
 * chrome). The two must not blur.
 *
 * Copy is Indonesian and traveler-facing; the console chrome around it stays
 * English for the analyst. Both use Indonesian number formatting.
 */
import type { HoldStatus, NotificationDraft } from "@/lib/windfall/types";
import { mayRenderDeadline } from "@/lib/windfall/types";
import { idr, pct } from "@/lib/windfall/format";
import { PreviewTag } from "./primitives";

/**
 * PricePanel — old price struck through, new price in mono, rationed note.
 *
 * The deadline slot renders only when a carrier genuinely guaranteed the fare.
 * There is no code path that produces one otherwise, which is how the design
 * system's no-fake-countdowns rule is enforced rather than merely intended.
 */
export function PricePanel({
  newPrice,
  oldPrice,
  note,
  noteTone = "neutral",
  hold,
}: {
  newPrice: number;
  oldPrice?: number | null;
  note?: string;
  noteTone?: "neutral" | "signal";
  hold?: HoldStatus;
}) {
  const showDeadline = hold ? mayRenderDeadline(hold) : false;
  return (
    <div
      style={{
        borderRadius: "var(--wf-radius-md)",
        background: "var(--wf-surface)",
        padding: "16px 18px",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 16,
          flexWrap: "wrap",
        }}
      >
        <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
          {oldPrice ? (
            <span
              className="wf-mono"
              style={{ fontSize: 12, color: "var(--wf-ink-3)", textDecoration: "line-through" }}
            >
              {idr(oldPrice)}
            </span>
          ) : null}
          <span className="wf-mono" style={{ fontSize: 22, fontWeight: 500, color: "var(--wf-ink)" }}>
            {idr(newPrice)}
          </span>
        </div>
        {note && (
          <span
            className="wf-mono"
            style={{
              fontSize: 11,
              textAlign: "right",
              whiteSpace: "pre-line",
              color: noteTone === "signal" ? "var(--wf-signal-ink)" : "var(--wf-ink-3)",
            }}
          >
            {note}
          </span>
        )}
      </div>
      {showDeadline && hold && (
        <div
          className="wf-mono"
          style={{ marginTop: 12, fontSize: 11, lineHeight: 1.6, color: "var(--wf-amber)" }}
        >
          Harga penerbangan dijamin {hold.carrier} sampai {hold.expires_at}. Tarif hotel
          dihitung ulang saat pembayaran.
        </div>
      )}
    </div>
  );
}
