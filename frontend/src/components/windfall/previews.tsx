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
          Harga penerbangan dijamin {hold.carrier} sampai {hold.expiresAt}. Tarif hotel
          dihitung ulang saat pembayaran.
        </div>
      )}
    </div>
  );
}

/**
 * EmailPreview — a drafted message, rendered as a real inbox item.
 *
 * Reads as correspondence, not as system output: sans-serif, natural
 * sentences, mail chrome. The reasoning timeline beside it reads as machine
 * output. Blurring the two would make the trace look like marketing and the
 * message look like a log line.
 *
 * The reminder path renders here identically to every other outcome. It has a
 * subject, a body, a price panel and a CTA -- it is a message someone
 * receives, not a blank state.
 */
export function EmailPreview({
  draft,
  hold,
  originalTotal,
  finalTotal,
  saving,
  savingPct,
  sent = false,
}: {
  draft: NotificationDraft;
  hold: HoldStatus;
  originalTotal: number;
  finalTotal: number;
  saving: number;
  savingPct: number | null;
  sent?: boolean;
}) {
  const changed = saving > 0;
  return (
    <div>
      <div style={{ marginBottom: 10 }}>
        <PreviewTag />
      </div>
      <article
        style={{
          borderRadius: "var(--wf-radius-md)",
          background: "var(--wf-white)",
          overflow: "hidden",
          boxShadow: "var(--wf-ring-border)",
        }}
      >
        <header
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: 12,
            padding: "12px 15px",
            background: "var(--wf-surface-2)",
            borderBottom: "var(--wf-border-hair)",
          }}
        >
          <span
            className="wf-serif"
            aria-hidden
            style={{
              flexShrink: 0,
              width: 22,
              height: 22,
              borderRadius: 11,
              background: "var(--wf-ink)",
              color: "var(--wf-paper)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 13,
            }}
          >
            W
          </span>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 13, fontWeight: 500, color: "var(--wf-ink)" }}>
              {draft.subject}
            </div>
            <div className="wf-mono" style={{ marginTop: 2, fontSize: 10, color: "var(--wf-ink-3)" }}>
              Windfall &middot; {sent ? "delivered" : "draft, not yet sent"}
            </div>
          </div>
        </header>

        <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 14 }}>
          {draft.bodyParagraphs.map((p, i) => (
            <p key={i} style={{ margin: 0, fontSize: 13, lineHeight: 1.7, color: "var(--wf-ink-2)" }}>
              {p}
            </p>
          ))}

          <PricePanel
            newPrice={finalTotal}
            oldPrice={changed ? originalTotal : null}
            note={changed ? `Hemat ${idr(saving)}\n${pct(savingPct)}` : "Harga tidak berubah"}
            noteTone={changed ? "signal" : "neutral"}
            hold={hold}
          />

          <span
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: "100%",
              padding: "13px 20px",
              fontSize: 13,
              fontWeight: 500,
              borderRadius: "var(--wf-radius-md)",
              background: changed ? "var(--wf-cta)" : "transparent",
              boxShadow: changed ? "none" : "var(--wf-ring-ink)",
              color: changed ? "var(--wf-cta-ink)" : "var(--wf-ink)",
            }}
          >
            {draft.ctaLabel}
          </span>

          {draft.channelNote && (
            <p className="wf-mono" style={{ margin: 0, fontSize: 11, color: "var(--wf-ink-3)" }}>
              {draft.channelNote}
            </p>
          )}
        </div>
      </article>
    </div>
  );
}

/**
 * WhatsAppPreview — the same decision, on the channel most Indonesian
 * travelers actually read. Dark shell, single received bubble.
 */
export function WhatsAppPreview({
  draft,
  finalTotal,
  saving,
}: {
  draft: NotificationDraft;
  finalTotal: number;
  saving: number;
}) {
  const changed = saving > 0;
  return (
    <div>
      <div style={{ marginBottom: 10 }}>
        <PreviewTag />
      </div>
      <div
        style={{
          borderRadius: "var(--wf-radius-md)",
          background: "var(--wf-wa-bg)",
          overflow: "hidden",
          boxShadow: "var(--wf-ring-border)",
        }}
      >
        <header
          style={{
            display: "flex",
            alignItems: "center",
            gap: 9,
            padding: "10px 14px",
            background: "var(--wf-wa-hd)",
          }}
        >
          <span
            className="wf-serif"
            aria-hidden
            style={{
              width: 24,
              height: 24,
              borderRadius: 12,
              background: "var(--wf-paper)",
              color: "var(--wf-ink)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 13,
            }}
          >
            W
          </span>
          <div>
            <div style={{ fontSize: 12, fontWeight: 700, color: "var(--wf-white)" }}>Windfall</div>
            <div className="wf-mono" style={{ fontSize: 10, color: "var(--wf-ink-3)" }}>
              Akun bisnis
            </div>
          </div>
        </header>

        <div style={{ padding: 15 }}>
          <div
            style={{
              maxWidth: 490,
              borderRadius: "2px 10px 10px 10px",
              background: "var(--wf-white)",
              boxShadow: "var(--wf-shadow-bubble)",
              padding: 13,
            }}
          >
            <p style={{ margin: "0 0 10px", fontSize: 13, lineHeight: 1.7, color: "var(--wf-ink)" }}>
              {draft.whatsapp}
            </p>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                gap: 12,
                padding: "9px 0",
                borderTop: "1px solid var(--wf-rule)",
              }}
            >
              <span className="wf-mono" style={{ fontSize: 16, color: "var(--wf-ink)" }}>
                {idr(finalTotal)}
              </span>
              <span
                className="wf-mono"
                style={{ fontSize: 11, color: changed ? "var(--wf-signal-ink)" : "var(--wf-ink-3)" }}
              >
                {changed ? `Hemat ${idr(saving)}` : "Harga tidak berubah"}
              </span>
            </div>
            <div
              style={{
                textAlign: "center",
                marginTop: 10,
                padding: "11px 14px",
                borderRadius: 8,
                background: changed ? "var(--wf-cta)" : "var(--wf-surface)",
                color: changed ? "var(--wf-cta-ink)" : "var(--wf-ink)",
                fontSize: 13,
                fontWeight: 600,
              }}
            >
              {draft.ctaLabel}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
