"use client";

/**
 * BrowseView — the abandoned-cart list.
 *
 * A plain list, on purpose. No sort, no tier filter, no pagination, no counts.
 * The penyisihan scope rule is a single input with no analytics dashboard, and
 * a sort/filter toolbar over a queue is exactly what invites the question of
 * whether this is a dashboard. Six cards need no navigation.
 */
import type { QueueEntry } from "@/lib/windfall/types";
import { TravelerCard } from "./TravelerCard";

export function BrowseView({
  queue,
  onSelect,
}: {
  queue: QueueEntry[];
  /* Fires the run AND the transition: the pending state lives on the
     pipeline screen, never as a busy card in this list. */
  onSelect: (travelerId: string, travelerName: string) => void;
}) {
  return (
    <div className="wf-fade" style={{ display: "flex", flexDirection: "column", gap: 22 }}>
      <header style={{ textAlign: "center" }}>
        <h1
          className="wf-mono wf-h1"
          style={{
            margin: 0,
            fontSize: 44,
            fontWeight: 700,
            letterSpacing: "-0.01em",
            lineHeight: 1.08,
            color: "var(--wf-ink)",
          }}
        >
          Abandoned Carts
        </h1>
        <p
          style={{
            margin: "14px auto 0",
            maxWidth: "56ch",
            fontSize: 15,
            lineHeight: 1.65,
            color: "var(--wf-ink-2)",
            textWrap: "pretty",
          }}
        >
          Pick one cart to run the pipeline. Every decision reads two signals: how
          often this traveler waits for a promotion, and how far the cart sits from
          what they usually spend. A price intervention needs both to agree. The tier
          shown on each card is a provisional estimate, not the Classifier&rsquo;s verdict.
        </p>
      </header>

      <div
        role="group"
        aria-label="Abandoned carts awaiting a decision"
        className="wf-grid-2"
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 20,
        }}
      >
        {queue.map((entry) => (
          <TravelerCard key={entry.travelerId} entry={entry} onSelect={onSelect} />
        ))}
      </div>
    </div>
  );
}
