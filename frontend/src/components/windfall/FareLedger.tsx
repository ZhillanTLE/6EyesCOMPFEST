/**
 * FareLedger — the signature artifact. One row per rebuild attempt.
 *
 * Three row states, and keeping them distinct is the whole point:
 *
 *   pass       cleared the tier threshold (Signal tint)
 *   fail       priced, but the saving missed the threshold (Halt tint)
 *   unavailable  nothing came back for this rung at all (no tint)
 *
 * A rung that found an option and rejected it is evidence that restraint was
 * earned. Collapsing it into "nothing found" would erase the argument.
 */
import type { LadderAttempt } from "@/lib/windfall/types";
import { idr, pct } from "@/lib/windfall/format";
import { StatusPill } from "./primitives";

function rowState(a: LadderAttempt): "pass" | "fail" | "unavailable" {
  if (!a.available) return "unavailable";
  return a.cleared ? "pass" : "fail";
}

const ROW_BG = {
  pass: "var(--wf-signal-tint)",
  fail: "var(--wf-halt-tint)",
  unavailable: "transparent",
};
const DELTA_INK = {
  pass: "var(--wf-signal-ink)",
  fail: "var(--wf-halt)",
  unavailable: "var(--wf-ink-3)",
};
const TONE = { pass: "pass", fail: "fail", unavailable: "neutral" } as const;
const STATUS_TEXT = {
  pass: "Cleared",
  fail: "Below threshold",
  unavailable: "Not available",
};

export function FareLedger({
  attempts,
  footerLeft,
  footerRight,
}: {
  attempts: LadderAttempt[];
  footerLeft?: string;
  footerRight?: string;
}) {
  return (
    <div
      style={{
        borderRadius: "var(--wf-radius-md)",
        overflow: "hidden",
        boxShadow: "var(--wf-ring-border)",
      }}
    >
      <div
        className="wf-eyebrow"
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "8px 14px",
          background: "var(--wf-surface)",
          borderBottom: "1px solid var(--wf-border)",
        }}
      >
        <span style={{ width: 22 }}>#</span>
        <span style={{ flex: 1 }}>Attempt</span>
        <span style={{ width: 116, textAlign: "right" }}>Total</span>
        <span style={{ width: 64, textAlign: "right" }}>Delta</span>
        <span style={{ width: 116, textAlign: "right" }}>Status</span>
      </div>

      {attempts.map((a, i) => {
        const state = rowState(a);
        return (
          <div
            key={a.index}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "10px 14px",
              background: ROW_BG[state],
              borderBottom:
                i < attempts.length - 1 || footerLeft ? "1px solid var(--wf-rule)" : "none",
            }}
          >
            <span className="wf-mono" style={{ width: 22, fontSize: 12, color: "var(--wf-ink-3)" }}>
              {String(a.index).padStart(2, "0")}
            </span>
            <span
              className="wf-mono"
              style={{ flex: 1, minWidth: 0, fontSize: 12, lineHeight: 1.6, color: "var(--wf-ink-2)" }}
            >
              {a.label}
              {a.hotel && (
                <span style={{ color: "var(--wf-ink-3)" }}>
                  {" "}
                  &middot; {a.hotel.name}
                </span>
              )}
            </span>
            <span
              className="wf-mono"
              style={{ width: 116, textAlign: "right", fontSize: 12, color: "var(--wf-ink)" }}
            >
              {a.totalIdr === null ? "—" : idr(a.totalIdr)}
            </span>
            <span
              className="wf-mono"
              style={{ width: 64, textAlign: "right", fontSize: 12, color: DELTA_INK[state] }}
            >
              {pct(a.delta)}
            </span>
            <span style={{ width: 116, textAlign: "right" }}>
              <StatusPill tone={TONE[state]}>{STATUS_TEXT[state]}</StatusPill>
            </span>
          </div>
        );
      })}

      {(footerLeft || footerRight) && (
        <div
          className="wf-mono"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 12,
            padding: "13px 14px",
            background: "var(--wf-surface)",
            borderTop: "1px solid var(--wf-border)",
            fontSize: 11,
            lineHeight: 1.6,
            color: "var(--wf-ink-2)",
          }}
        >
          <span>{footerLeft}</span>
          {footerRight && <span>{footerRight}</span>}
        </div>
      )}
    </div>
  );
}
