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
          Cart yang ditinggalkan
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
          Pilih satu cart untuk menjalankan pipeline. Setiap keputusan dibaca dari dua
          sinyal: seberapa sering wisatawan menunggu promo, dan seberapa jauh cart ini
          dari pengeluaran biasanya. Diskon hanya keluar bila keduanya sepakat.
        </p>
      </header>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))",
          gap: 20,
        }}
      >
        {queue.map((entry) => (
          <TravelerCard
            key={entry.traveler_id}
            entry={entry}
            busy={busyId === entry.traveler_id}
            onSelect={onSelect}
          />
        ))}
      </div>
    </div>
  );
}
