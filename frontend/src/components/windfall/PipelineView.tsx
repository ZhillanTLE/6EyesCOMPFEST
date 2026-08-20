"use client";

/**
 * PipelineView — the core screen. Three agents reasoning over one cart.
 *
 * The three stages deliberately do not render alike. The Classifier emits
 * arrow-prefixed reasoning lines and a tier. The Searcher emits the fare
 * ledger, revealed row by row across its real duration. The Notifier emits
 * drafted copy. Giving them a shared layout would flatten three different
 * kinds of work into one shape.
 */
import type { RecoveryResult } from "@/lib/windfall/types";
import { plainPct, seconds } from "@/lib/windfall/format";
import { stageStatus, useReplay } from "@/lib/windfall/replay";
import { AgentStage } from "./AgentStage";
import { FareLedger } from "./FareLedger";
import { OutcomeCard, OutcomeNote } from "./OutcomeCard";
import { EmailPreview, WhatsAppPreview } from "./previews";
import { Skeleton, TierBadge } from "./primitives";

function stageMs(result: RecoveryResult, stage: string): number {
  return result.timings.find((t) => t.stage === stage)?.duration_ms ?? 0;
}

export function PipelineView({
  result,
  onBack,
}: {
  result: RecoveryResult;
  onBack: () => void;
}) {
  const halted = result.decision.outcome === "error";
  const { phase, revealed } = useReplay(result);
  const { classification, gate, decision, hold, notification } = result;

  const shown = phase >= 3 ? decision.attempts.length : revealed;
  const attempts = decision.attempts.slice(0, shown);
  const ladderComplete = phase >= 3;
  const winner = decision.attempts.find((a) => a.cleared);

  return (
    <div className="wf-fade" style={{ display: "flex", flexDirection: "column", gap: 26 }}>
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
          &larr; Semua cart
        </button>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontSize: 15, fontWeight: 500 }}>{result.traveler_name}</div>
          <div className="wf-mono" style={{ marginTop: 2, fontSize: 11, color: "var(--wf-ink-3)" }}>
            {result.cart_id}
          </div>
        </div>
      </header>

      <section aria-label="Agent reasoning" style={{ display: "flex", flexDirection: "column" }}>
        <AgentStage
          title="Classifier Agent"
          model="gemini"
          status={stageStatus(phase, "classifier")}
          duration={phase >= 2 ? seconds(stageMs(result, "classifier")) : undefined}
          reasons={phase >= 2 ? classification.reasoning : []}
        >
          {phase < 2 && (
            <div style={{ display: "flex", flexDirection: "column", gap: 8, maxWidth: 440 }}>
              <Skeleton width="88%" height={12} />
              <Skeleton width="70%" height={12} />
            </div>
          )}
          {phase >= 2 && (
            <TierBadge
              tier={classification.tier}
              threshold={`Ambang ${plainPct(classification.threshold)}`}
              source={classification.tier_source}
            />
          )}
        </AgentStage>

        <AgentStage
          title="Searcher Agent"
          model="gemini + mcp"
          status={stageStatus(phase, "searcher", halted)}
          duration={phase >= 3 && !halted ? seconds(stageMs(result, "searcher")) : undefined}
        >
          {halted && phase >= 2 && (
            <OutcomeNote>
              Inventaris maskapai sedang tidak tersedia, sehingga rebuild tidak dapat
              dijalankan. Cart ini dilewati pada siklus ini.
            </OutcomeNote>
          )}

          {!halted && phase === 2 && attempts.length === 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: 8, maxWidth: 460 }}>
              <Skeleton width="92%" height={12} />
              <Skeleton width="74%" height={12} />
              <Skeleton width="83%" height={12} />
            </div>
          )}

          {/* Gate closed, so no ladder ran. Saying which signal closed it is
              the difference between a decision and an omission. */}
          {!halted && ladderComplete && decision.attempts.length === 0 && (
            <OutcomeNote>
              <strong style={{ color: "var(--wf-ink)" }}>Ladder tidak dijalankan.</strong>{" "}
              {gate.reason}
            </OutcomeNote>
          )}

          {!halted && attempts.length > 0 && (
            <>
              <FareLedger
                attempts={attempts}
                footerLeft={
                  ladderComplete
                    ? `Ambang tingkatan ${classification.tier} ${plainPct(classification.threshold)}`
                    : undefined
                }
                footerRight={
                  ladderComplete
                    ? winner
                      ? `Berhenti di percobaan ${String(winner.index).padStart(2, "0")}`
                      : "Tidak ada yang memenuhi ambang"
                    : undefined
                }
              />
              {!ladderComplete && (
                <div
                  className="wf-mono"
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    marginTop: 10,
                    fontSize: 12,
                    color: "var(--wf-ink-3)",
                  }}
                >
                  <span
                    aria-hidden
                    className="wf-spin"
                    style={{
                      width: 14,
                      height: 14,
                      border: "2px solid var(--wf-border)",
                      borderTopColor: "var(--wf-ink)",
                      borderRadius: "50%",
                      display: "inline-block",
                    }}
                  />
                  Menguji percobaan berikutnya…
                </div>
              )}
            </>
          )}
        </AgentStage>

        <AgentStage
          title="Notifier Agent"
          model="gemini"
          status={halted ? "waiting" : stageStatus(phase, "notifier")}
          duration={phase >= 4 && !halted ? seconds(stageMs(result, "notifier")) : undefined}
          reasons={
            phase >= 4 && notification
              ? [
                  `Nada disesuaikan untuk tingkatan ${classification.tier}`,
                  "Menjelaskan keputusan yang diambil, bukan urgensi generik",
                ]
              : []
          }
          last
        >
          {!halted && phase === 3 && (
            <div style={{ display: "flex", flexDirection: "column", gap: 8, maxWidth: 420 }}>
              <Skeleton width="80%" height={12} />
              <Skeleton width="64%" height={12} />
            </div>
          )}
        </AgentStage>
      </section>

      {phase >= 4 && (
        <OutcomeCard
          decision={decision}
          gate={gate}
          originalTotal={result.original_total_idr}
          threshold={classification.threshold}
        />
      )}

      {phase >= 4 && notification && (
        <section
          aria-label="Pratinjau notifikasi"
          className="wf-fade"
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
            gap: 20,
            alignItems: "start",
          }}
        >
          <EmailPreview
            draft={notification}
            hold={hold}
            originalTotal={result.original_total_idr}
            finalTotal={decision.final_total_idr ?? result.original_total_idr}
            saving={decision.saving_idr}
            savingPct={decision.saving_pct}
          />
          <WhatsAppPreview
            draft={notification}
            finalTotal={decision.final_total_idr ?? result.original_total_idr}
            saving={decision.saving_idr}
          />
        </section>
      )}
    </div>
  );
}
