"use client";

/**
 * Stage replay, paced by the durations the server actually measured.
 *
 * The endpoint is synchronous: the entire trace arrives in one response. So
 * the console is not waiting on anything here -- it is replaying a completed
 * run at the speed it really took, using the per-stage wall-clock the backend
 * recorded.
 *
 * That distinction is worth being precise about, because the prototype derived
 * its stage durations from a hash of the cart id and presented them as real.
 * These come from time.perf_counter around each stage (live mode) or from a
 * recorded live run (fixture mode). Either way the number on screen is a
 * duration that actually happened.
 */
import { useEffect, useMemo, useRef, useState } from "react";
import type { RecoveryResult, StageName } from "./types";

export type Phase = 0 | 1 | 2 | 3 | 4;

export interface ReplayState {
  /** 0 idle · 1 classifying · 2 searching · 3 drafting · 4 complete */
  phase: Phase;
  /** How many ladder rows have been revealed so far. */
  revealed: number;
  done: boolean;
}

function durations(result: RecoveryResult): Record<StageName, number> {
  const out: Record<StageName, number> = { classifier: 0, searcher: 0, notifier: 0 };
  for (const t of result.timings) out[t.stage] = t.duration_ms;
  return out;
}

export function useReplay(result: RecoveryResult | null, enabled = true): ReplayState {
  const [state, setState] = useState<ReplayState>({ phase: 0, revealed: 0, done: false });
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);

  const key = result ? `${result.cart_id}:${result.timings.map((t) => t.duration_ms).join("-")}` : "";

  const plan = useMemo(() => (result ? durations(result) : null), [result]);

  useEffect(() => {
    // Every handle is tracked and cleared: the pipeline is restartable at any
    // moment, and a leaked timer would advance the phase of a run the analyst
    // has already navigated away from.
    for (const t of timers.current) clearTimeout(t);
    timers.current = [];

    if (!result || !plan) {
      setState({ phase: 0, revealed: 0, done: false });
      return;
    }

    if (!enabled) {
      setState({ phase: 4, revealed: result.decision.attempts.length, done: true });
      return;
    }

    const at = (ms: number, fn: () => void) => {
      timers.current.push(setTimeout(fn, ms));
    };

    setState({ phase: 1, revealed: 0, done: false });

    const attempts = result.decision.attempts.length;
    const tClassifier = plan.classifier;
    const tSearcher = plan.searcher;

    at(tClassifier, () => setState({ phase: 2, revealed: 0, done: false }));

    // Ladder rows appear one at a time across the searcher's real duration, so
    // the reveal is a rendering of how long the search took rather than an
    // animation invented to look busy.
    if (attempts > 0) {
      const step = tSearcher / (attempts + 1);
      for (let i = 1; i <= attempts; i += 1) {
        at(tClassifier + step * i, () =>
          setState((s) => (s.phase >= 2 ? { ...s, revealed: i } : s)),
        );
      }
    }

    at(tClassifier + tSearcher, () =>
      setState({ phase: 3, revealed: attempts, done: false }),
    );
    at(tClassifier + tSearcher + plan.notifier, () =>
      setState({ phase: 4, revealed: attempts, done: true }),
    );

    return () => {
      for (const t of timers.current) clearTimeout(t);
      timers.current = [];
    };
    // `key` collapses the result identity to its cart and its timings.
  }, [key, enabled, result, plan]);

  return state;
}

/** Stage status for a given phase, matching AgentStage's vocabulary. */
export function stageStatus(
  phase: Phase,
  stage: StageName,
  halted = false,
): "waiting" | "running" | "done" | "halted" {
  const order: StageName[] = ["classifier", "searcher", "notifier"];
  const index = order.indexOf(stage);
  if (halted && index >= 1) return index === 1 ? "halted" : "waiting";
  if (phase === 0) return "waiting";
  if (phase > index + 1) return "done";
  if (phase === index + 1) return "running";
  return "waiting";
}
