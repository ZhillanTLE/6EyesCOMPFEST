/**
 * AgentStage — one node on the reasoning timeline.
 *
 * The three agents deliberately do NOT render identically. The Classifier
 * emits short arrow-prefixed reasoning lines, the Searcher emits the fare
 * ledger, the Notifier emits drafted copy. Matching their layouts would flatten
 * three different kinds of work into one shape.
 *
 * The duration shown is measured, never synthesised.
 */
import type { ReactNode } from "react";
import { AgentAvatar, type AvatarAgent, type AvatarState } from "./AgentAvatar";
import { ModelTag } from "./primitives";

export type StageStatus = "waiting" | "running" | "done" | "halted";

/* Spoken status. The visual state is a dot and a colour, neither of which a
   screen reader conveys. */
const STATUS_WORD: Record<StageStatus, string> = {
  waiting: "waiting",
  running: "running",
  done: "complete",
  halted: "halted",
};

export function AgentStage({
  title,
  model,
  duration,
  status = "waiting",
  reasons = [],
  last = false,
  children,
  avatar,
}: {
  title: string;
  model?: string;
  duration?: string;
  status?: StageStatus;
  reasons?: string[];
  last?: boolean;
  children?: ReactNode;
  avatar?: { agent: AvatarAgent; state: AvatarState };
}) {
  const dot: Record<StageStatus, React.CSSProperties> = {
    done: { background: "var(--wf-ink)", boxShadow: "inset 0 0 0 2px var(--wf-ink)" },
    running: { background: "var(--wf-ink)", boxShadow: "inset 0 0 0 2px var(--wf-ink)" },
    halted: { background: "var(--wf-halt)", boxShadow: "inset 0 0 0 2px var(--wf-halt)" },
    waiting: { background: "var(--wf-white)", boxShadow: "inset 0 0 0 2px var(--wf-border)" },
  };
  const titleColor = status === "waiting" ? "var(--wf-ink-3)" : "var(--wf-ink)";

  return (
    <div
      role="listitem"
      aria-label={`${title}: ${STATUS_WORD[status]}${duration ? `, ${duration}` : ""}`}
      style={{
        position: "relative",
        /* The avatar well is wider than the dot it replaces and overhangs the
           rail on both sides, so the body has to start clear of it. */
        paddingLeft: avatar ? 36 : 20,
        paddingBottom: last ? 0 : 26,
        borderLeft: last ? "2px solid transparent" : "2px solid var(--wf-rule)",
      }}
    >
      {avatar ? (
        <AgentAvatar agent={avatar.agent} state={avatar.state} />
      ) : (
        <span
          aria-hidden
          style={{
            position: "absolute",
            left: -7,
            top: 4,
            width: 12,
            height: 12,
            borderRadius: 6,
            ...dot[status],
          }}
        />
      )}
      <div style={{ display: "flex", alignItems: "center", gap: 9, flexWrap: "wrap" }}>
        <span style={{ fontSize: 13, fontWeight: 500, lineHeight: 1.6, color: titleColor }}>
          {title}
        </span>
        {model && <ModelTag>{model}</ModelTag>}
        {duration && (
          <span className="wf-eyebrow" style={{ marginLeft: "auto" }}>
            {duration}
          </span>
        )}
      </div>

      {reasons.length > 0 && (
        <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 5 }}>
          {reasons.map((r, i) => (
            <div
              key={i}
              className="wf-mono"
              style={{ display: "flex", gap: 8, fontSize: 12, lineHeight: 1.6, color: "var(--wf-ink-2)" }}
            >
              <span aria-hidden style={{ color: "var(--wf-ink-3)" }}>
                &rarr;
              </span>
              <span>{r}</span>
            </div>
          ))}
        </div>
      )}

      {children && <div style={{ marginTop: 12 }}>{children}</div>}
    </div>
  );
}
