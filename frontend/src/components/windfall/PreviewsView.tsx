"use client";

/**
 * PreviewsView -- the third screen: exactly what the traveler will receive.
 *
 * The handoff describes previews as its own view, and it earns one. On the
 * pipeline screen the previews sat below a completed trace, which framed them
 * as one more artefact of the run; here they are the only thing on the page,
 * which is the right framing for the one irreversible action in the product.
 *
 * Note the divergence from the prototype, which reached this view only AFTER
 * approving and headed it "Disetujui". That inverts the product: CLAUDE.md is
 * explicit that the analyst approves before anything is sent, and the handoff
 * README states the purpose as reading the message *before* it sends. So the
 * approval control lives here, below the previews, and the sent state renders
 * on this same screen afterwards.
 */
import type { RecoveryResult, SendReceipt } from "@/lib/windfall/types";
import { ApprovalBar } from "./ApprovalBar";
import { EmailPreview, WhatsAppPreview } from "./previews";

/* Quoted mail-client chrome. Decorative and hidden from the accessibility
   tree -- a screen reader gets the message, not the window buttons. */
function MailChrome() {
  const dots = ["var(--wf-chrome-close)", "var(--wf-chrome-min)", "var(--wf-chrome-max)"];
  return (
    <div
      aria-hidden
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "9px 12px",
        background: "var(--wf-surface-2)",
        borderBottom: "1px solid var(--wf-rule)",
      }}
    >
      {dots.map((c) => (
        <span key={c} style={{ width: 10, height: 10, borderRadius: "50%", background: c }} />
      ))}
      <span className="wf-mono" style={{ marginLeft: 8, fontSize: 11, color: "var(--wf-ink-3)" }}>
        Inbox &middot; 1 pesan baru
      </span>
    </div>
  );
}

export function PreviewsView({
  result,
  onBack,
  receipt,
  sending,
  onApprove,
}: {
  result: RecoveryResult;
  onBack: () => void;
  receipt: SendReceipt | null;
  sending: boolean;
  onApprove: () => void;
}) {
  const { decision, hold, notification } = result;
  if (!notification) return null;

  return (
    <div className="wf-fade" style={{ display: "flex", flexDirection: "column", gap: 22 }}>
      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 16,
          flexWrap: "wrap",
        }}
      >
        <button
          type="button"
          onClick={onBack}
          className="wf-mono"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            padding: "9px 16px",
            fontSize: 13,
            fontWeight: 700,
            border: "none",
            borderRadius: 4,
            background: "var(--wf-ink)",
            color: "var(--wf-paper)",
            cursor: "pointer",
          }}
        >
          &larr; Pipeline
        </button>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontSize: 15, fontWeight: 500 }}>{result.travelerName}</div>
          <div className="wf-mono" style={{ marginTop: 2, fontSize: 11, color: "var(--wf-ink-3)" }}>
            {decision.outcome} &middot; {result.cartId}
          </div>
        </div>
      </header>

      <p
        style={{
          margin: 0,
          maxWidth: "68ch",
          fontSize: 13,
          lineHeight: 1.7,
          color: "var(--wf-ink-2)",
        }}
      >
        This is the message as the traveler will read it. Nothing has been
        delivered yet. Email sends on approval; WhatsApp stays a preview,
        because the Business API needs verified business status and
        pre-approved templates.
      </p>

      <section
        aria-label="Notification previews"
        className="wf-grid-2"
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
          gap: 20,
          alignItems: "start",
        }}
      >
        <div>
          <div
            style={{
              borderRadius: "var(--wf-radius-md)",
              overflow: "hidden",
              background: "var(--wf-surface)",
              boxShadow: "var(--wf-ring-border)",
            }}
          >
            <MailChrome />
            <div style={{ padding: 16 }}>
              <EmailPreview
                draft={notification}
                hold={hold}
                originalTotal={result.originalTotalIdr}
                finalTotal={decision.finalTotalIdr ?? result.originalTotalIdr}
                saving={decision.savingIdr}
                savingPct={decision.savingPct}
                sent={receipt?.state === "sent"}
              />
            </div>
          </div>
        </div>

        <WhatsAppPreview
          draft={notification}
          finalTotal={decision.finalTotalIdr ?? result.originalTotalIdr}
          saving={decision.savingIdr}
        />
      </section>

      <ApprovalBar
        receipt={receipt}
        sending={sending}
        disabled={false}
        onApprove={onApprove}
      />
    </div>
  );
}
