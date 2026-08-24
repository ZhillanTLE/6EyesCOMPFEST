"use client";

/**
 * ApprovalBar — the explicit, separate control that actually sends.
 *
 * Kept visually and functionally distinct from the analysis trigger. Running
 * the pipeline drafts a message; delivering it needs its own deliberate click,
 * so clicking through six travelers to read their traces sends nothing.
 *
 * Reports three outcomes honestly. "Suppressed" is what SEND_ENABLED=false
 * produces -- the flow ran, nothing left the building -- and it is never
 * dressed up as "sent".
 */
import type { SendReceipt } from "@/lib/windfall/types";

export function ApprovalBar({
  receipt,
  sending,
  disabled,
  disabledReason,
  onApprove,
  onReplay,
}: {
  receipt: SendReceipt | null;
  sending: boolean;
  disabled: boolean;
  disabledReason?: string;
  onApprove: () => void;
  onReplay?: () => void;
}) {
  const tone =
    receipt?.state === "sent"
      ? { bg: "var(--wf-signal-tint)", ink: "var(--wf-signal-ink)" }
      : receipt?.state === "failed"
        ? { bg: "var(--wf-halt-tint)", ink: "var(--wf-halt)" }
        : { bg: "var(--wf-amber-tint)", ink: "var(--wf-amber)" };

  return (
    <section
      aria-label="Approval"
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 16,
        flexWrap: "wrap",
        padding: "16px 18px",
        borderRadius: "var(--wf-radius-md)",
        background: "var(--wf-white)",
        boxShadow: "var(--wf-ring-border)",
      }}
    >
      <div style={{ minWidth: 0 }}>
        <div className="wf-eyebrow">Analyst approval</div>
        <p style={{ margin: "6px 0 0", fontSize: 13, lineHeight: 1.6, color: "var(--wf-ink-2)", maxWidth: "62ch" }}>
          {disabled
            ? disabledReason
            : "The agents draft; they never send. Approving delivers the email to the demo inbox — WhatsApp stays a preview."}
        </p>

        {receipt && (
          <div
            role="status"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              marginTop: 10,
              padding: "6px 10px",
              borderRadius: "var(--wf-radius-sm)",
              background: tone.bg,
            }}
          >
            <span className="wf-mono" style={{ fontSize: 11, letterSpacing: "0.06em", textTransform: "uppercase", color: tone.ink }}>
              {receipt.state === "sent"
                ? `Sent to ${receipt.recipient}`
                : receipt.state === "suppressed"
                  ? "Sending suppressed"
                  : "Send failed"}
            </span>
            {receipt.detail && (
              <span style={{ fontSize: 12, color: "var(--wf-ink-2)" }}>{receipt.detail}</span>
            )}
          </div>
        )}
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 10, flexShrink: 0 }}>
        {onReplay && (
        <button
          type="button"
          onClick={onReplay}
          className="wf-mono"
          style={{
            padding: "11px 16px",
            fontSize: 12,
            letterSpacing: "0.06em",
            textTransform: "uppercase",
            border: "none",
            borderRadius: "var(--wf-radius-md)",
            background: "transparent",
            boxShadow: "var(--wf-ring-border)",
            color: "var(--wf-ink-2)",
            cursor: "pointer",
          }}
        >
          Replay
        </button>
        )}
        <button
          type="button"
          onClick={onApprove}
          disabled={disabled || sending || receipt?.state === "sent"}
          style={{
            padding: "13px 24px",
            fontSize: 13,
            fontWeight: 500,
            border: "none",
            borderRadius: "var(--wf-radius-md)",
            background: "var(--wf-approve)",
            color: "var(--wf-cta-ink)",
            cursor: disabled || sending ? "not-allowed" : "pointer",
            opacity: disabled || sending || receipt?.state === "sent" ? 0.45 : 1,
            transition: "opacity .12s ease",
          }}
        >
          {sending
            ? "Sending…"
            : receipt?.state === "sent"
              ? "Approved and sent"
              : "Approve and send"}
        </button>
      </div>
    </section>
  );
}
