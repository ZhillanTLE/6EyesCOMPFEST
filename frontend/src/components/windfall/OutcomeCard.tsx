/**
 * OutcomeCard — the pipeline verdict.
 *
 * Renamed from the bundle's DecisionCard, and "hold" is gone as an outcome
 * name: it collided with Hold Order, the airline price freeze. The no-discount
 * outcome is `reminder`.
 *
 * EQUAL VISUAL WEIGHT IS THE CONTRACT HERE. Every outcome gets the same frame,
 * the same header treatment and the same three-cell reconciliation grid --
 * reminder included. The prototype rendered it as a greyed-out "ladder
 * skipped" row, which read as the pipeline giving up. It is the opposite: it
 * is the product's differentiating decision, and it costs the partner nothing.
 */
import type { Decision, GateResult, Outcome } from "@/lib/windfall/types";
import { idr, pct, plainPct } from "@/lib/windfall/format";

const LABELS: Record<Outcome, string> = {
  rebuild: "REBUILD OFFER",
  lateral: "SAME-TIER SWAP",
  reminder: "REMINDER — NO DISCOUNT",
  alternative: "ALTERNATIVE SUGGESTED",
  error: "ATTEMPT HALTED",
};

const SUBTITLES: Record<Outcome, string> = {
  rebuild: "Hotel turun satu tingkat · penerbangan, tanggal, dan kawasan tetap",
  lateral: "Penginapan setara di kelas bintang yang sama · tidak ada penurunan kelas",
  reminder: "Akan tetap konversi tanpa diskon · margin mitra utuh",
  alternative: "Perjalanan asli tidak memenuhi ambang · alternatif sesuai anggaran",
  error: "Inventaris maskapai tidak tersedia · cart dilewati siklus ini",
};

function Cell({
  label,
  value,
  sub,
  tone = "ink",
}: {
  label: string;
  value: string;
  sub?: string;
  tone?: "ink" | "signal" | "muted";
}) {
  const ink =
    tone === "signal" ? "var(--wf-signal-ink)" : tone === "muted" ? "var(--wf-ink-3)" : "var(--wf-ink)";
  return (
    <div
      style={{
        background: tone === "signal" ? "var(--wf-signal-tint)" : "var(--wf-white)",
        padding: "15px 16px",
      }}
    >
      <div className="wf-eyebrow" style={{ color: tone === "signal" ? "var(--wf-signal-ink)" : undefined }}>
        {label}
      </div>
      <div
        className="wf-mono"
        style={{
          marginTop: 6,
          fontSize: 18,
          fontWeight: 600,
          letterSpacing: "-0.01em",
          whiteSpace: "nowrap",
          color: ink,
          textDecoration: tone === "muted" ? "line-through" : undefined,
        }}
      >
        {value}
      </div>
      {sub && (
        <div className="wf-mono" style={{ marginTop: 3, fontSize: 12, color: ink, opacity: 0.8 }}>
          {sub}
        </div>
      )}
    </div>
  );
}

export function OutcomeCard({
  decision,
  gate,
  originalTotal,
  threshold,
}: {
  decision: Decision;
  gate: GateResult;
  originalTotal: number;
  threshold: number;
}) {
  const outcome = decision.outcome;
  const intervened = outcome === "rebuild" || outcome === "lateral" || outcome === "alternative";

  return (
    <section
      className="wf-fade"
      style={{
        borderRadius: "var(--wf-radius-lg)",
        background: "var(--wf-white)",
        overflow: "hidden",
        boxShadow: "var(--wf-ring-rule)",
      }}
    >
      <header
        style={{
          padding: "13px 16px",
          background: "var(--wf-surface)",
          borderBottom: "var(--wf-border-hair)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
          <span className="wf-mono" style={{ fontSize: 13, fontWeight: 700, letterSpacing: "0.04em", color: "var(--wf-ink)" }}>
            {LABELS[outcome]}
          </span>
          <span className="wf-eyebrow" style={{ color: "var(--wf-signal-ink)" }}>
            {outcome === "error" ? "Tidak ada aksi" : "Margin mitra utuh"}
          </span>
        </div>
        <div style={{ marginTop: 4, fontSize: 11, lineHeight: 1.6, color: "var(--wf-ink-3)" }}>
          {SUBTITLES[outcome]}
        </div>
      </header>

      {/* Reconciliation. Identical shape on every path, reminder included. */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
          gap: 1,
          background: "var(--wf-rule)",
        }}
      >
        <Cell
          label="Cart semula"
          value={idr(originalTotal)}
          tone={intervened ? "muted" : "ink"}
        />
        <Cell
          label={intervened ? "Setelah disusun ulang" : "Harga akhir"}
          value={idr(decision.final_total_idr ?? originalTotal)}
        />
        <Cell
          label={intervened ? "Traveler hemat" : "Diskon diberikan"}
          value={intervened ? idr(decision.saving_idr) : "IDR 0"}
          sub={intervened ? pct(decision.saving_pct) : `Ambang ${plainPct(threshold)}`}
          tone="signal"
        />
      </div>

      <p
        style={{
          margin: 0,
          padding: "14px 16px",
          borderTop: "1px solid var(--wf-rule)",
          fontSize: 13,
          lineHeight: 1.65,
          color: "var(--wf-ink-2)",
          textWrap: "pretty",
        }}
      >
        {decision.rationale}
      </p>

      {/* The two signals, always shown, so the verdict stays arguable. */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: 1,
          background: "var(--wf-rule)",
          borderTop: "1px solid var(--wf-rule)",
        }}
      >
        <div style={{ background: "var(--wf-white)", padding: "12px 16px" }}>
          <div className="wf-eyebrow">Campaign share</div>
          <div className="wf-mono" style={{ marginTop: 5, fontSize: 15, color: "var(--wf-ink)" }}>
            {gate.campaign_share === null ? "Tidak terukur" : plainPct(gate.campaign_share)}
          </div>
        </div>
        <div style={{ background: "var(--wf-white)", padding: "12px 16px" }}>
          <div className="wf-eyebrow">Selisih anggaran</div>
          <div className="wf-mono" style={{ marginTop: 5, fontSize: 15, color: "var(--wf-ink)" }}>
            {plainPct(gate.budget_gap)}
          </div>
        </div>
        <div style={{ background: "var(--wf-white)", padding: "12px 16px" }}>
          <div className="wf-eyebrow">Margin dikorbankan</div>
          <div className="wf-mono" style={{ marginTop: 5, fontSize: 15, color: "var(--wf-signal-ink)" }}>
            {idr(decision.margin_conceded_idr)}
          </div>
        </div>
      </div>
    </section>
  );
}

/** Muted explanatory note used beside an outcome, e.g. the gate rationale. */
export function OutcomeNote({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        borderRadius: "var(--wf-radius-md)",
        background: "var(--wf-surface)",
        padding: "15px 12px",
        fontSize: 12.5,
        lineHeight: 1.65,
        color: "var(--wf-ink-2)",
      }}
    >
      {children}
    </div>
  );
}
