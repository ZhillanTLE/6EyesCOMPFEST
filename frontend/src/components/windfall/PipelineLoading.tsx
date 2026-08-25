"use client";

/**
 * PipelineLoading — the pipeline screen before the trace arrives.
 *
 * Clicking a cart must land on this screen immediately. The endpoint is
 * synchronous and the three agents really do call Gemini, so a run can take
 * anywhere from two seconds to over a minute; waiting on the browse list with
 * a "Running…" button left the analyst on the wrong screen, unsure whether the
 * click had registered. CLAUDE.md is explicit on both counts: selecting a card
 * TRANSITIONS to the pipeline view, and every agent stage needs a visible
 * pending state.
 *
 * The chrome is the real PipelineView's -- same back control, same three
 * AgentStage rows, same avatars -- so the swap when the trace lands changes
 * the content, not the layout.
 *
 * The Classifier is marked running and the two downstream stages waiting,
 * because that is the true state: the server works them in order. No progress
 * bar and no invented percentage; nothing here knows how far along the run is.
 */
import { AgentStage } from "./AgentStage";
import { Skeleton } from "./primitives";

export function PipelineLoading({
  travelerName,
  onBack,
}: {
  travelerName: string;
  onBack: () => void;
}) {
  return (
    <div
      className="wf-fade"
      style={{ position: "relative", display: "flex", flexDirection: "column", gap: 26 }}
    >
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
          &larr; All carts
        </button>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontSize: 15, fontWeight: 500 }}>{travelerName}</div>
          <div className="wf-mono" style={{ marginTop: 2, fontSize: 11, color: "var(--wf-ink-3)" }}>
            reasoning…
          </div>
        </div>
      </header>

      {/* Announced once. The trace itself takes over the live region when it
          arrives, so a screen reader hears the run start and then progress. */}
      <p
        aria-live="polite"
        aria-atomic="true"
        style={{
          position: "absolute",
          width: 1,
          height: 1,
          overflow: "hidden",
          clip: "rect(0 0 0 0)",
          whiteSpace: "nowrap",
        }}
      >
        Running the pipeline for {travelerName}. The agents are reasoning.
      </p>

      <section
        aria-label="Agent reasoning"
        aria-busy="true"
        role="list"
        style={{ display: "flex", flexDirection: "column" }}
      >
        <AgentStage
          title="Classifier Agent"
          model="gemini"
          status="running"
          avatar={{ agent: "classifier", state: "awake" }}
        >
          <div style={{ display: "flex", flexDirection: "column", gap: 8, maxWidth: 440 }}>
            <Skeleton width="88%" height={12} />
            <Skeleton width="70%" height={12} />
          </div>
        </AgentStage>

        <AgentStage
          title="Searcher Agent"
          model="gemini + mcp"
          status="waiting"
          avatar={{ agent: "searcher", state: "sleep" }}
        />

        <AgentStage
          title="Notification Curator Agent"
          model="gemini"
          status="waiting"
          last
          avatar={{ agent: "notifier", state: "sleep" }}
        />
      </section>

      <p
        className="wf-mono"
        style={{ margin: 0, fontSize: 11.5, lineHeight: 1.7, color: "var(--wf-ink-3)" }}
      >
        One synchronous request. The whole trace — tier, every ladder attempt,
        the decision and the drafted message — returns in a single response, so
        nothing appears until the agents have finished reasoning.
      </p>
    </div>
  );
}
