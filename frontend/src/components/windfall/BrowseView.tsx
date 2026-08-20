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
  busyId,
  onSelect,
}: {
  queue: QueueEntry[];
  busyId: string | null;
  onSelect: (travelerId: string) => void;
}) {
  return (
    <div className="wf-fade" style={{ display: "flex", flexDirection: "column", gap: 22 }}>
      <header>
        <h1
          className="wf-mono"
          style={{
            margin: 0,
            fontSize: 40,
            fontWeight: 700,
            letterSpacing: "-0.02em",
            lineHeight: 1.08,
            color: "var(--wf-ink)",
          }}
        >
          Abandoned carts
        </h1>
        <p
          style={{
            margin: "14px 0 0",
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
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))",
          gap: 20,
        }}
      >
        {queue.map((entry) => (
          <TravelerCard
            key={entry.travelerId}
            entry={entry}
            busy={busyId === entry.travelerId}
            onSelect={onSelect}
          />
        ))}
      </div>
    </div>
  );
}
