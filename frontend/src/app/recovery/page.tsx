"use client";

/**
 * The recovery console. One route, three views: pick a cart, watch the
 * pipeline reason over it, read the notification it drafted.
 *
 * State is small on purpose. The endpoint is synchronous, so there is no
 * streaming to coordinate and nothing to reconcile -- one POST returns the
 * whole trace, and the pipeline view replays it at the speed the server
 * measured.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { BrowseView, PipelineView, PreviewsView } from "@/components/windfall";
import { approveAndSend, fetchQueue, runRecovery } from "@/lib/windfall/api";
import type { QueueEntry, RecoveryResult, SendReceipt } from "@/lib/windfall/types";

export default function RecoveryConsole() {
  const [queue, setQueue] = useState<QueueEntry[]>([]);
  const [source, setSource] = useState<string>("live");
  const [result, setResult] = useState<RecoveryResult | null>(null);
  /* Which screen is showing. Derived from `result` for browse-vs-run, and
     from this flag for the step after the trace completes. */
  const [reviewing, setReviewing] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [receipt, setReceipt] = useState<SendReceipt | null>(null);
  const [sending, setSending] = useState(false);
  const [replayNonce, setReplayNonce] = useState(0);
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const abort = useRef<AbortController | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    fetchQueue(ctrl.signal)
      .then((r) => {
        setQueue(r.queue);
        setSource(r.source);
      })
      .catch((e: Error) => {
        if (e.name !== "AbortError") setError(e.message);
      });
    return () => ctrl.abort();
  }, []);

  useEffect(() => {
    try {
      const saved = localStorage.getItem("wf-theme");
      if (saved === "dark" || saved === "light") setTheme(saved);
    } catch {
      /* storage unavailable; the light default is fine */
    }
  }, []);

  const toggleTheme = useCallback(() => {
    setTheme((t) => {
      const next = t === "dark" ? "light" : "dark";
      try {
        localStorage.setItem("wf-theme", next);
      } catch {
        /* non-fatal */
      }
      return next;
    });
  }, []);

  const select = useCallback(async (travelerId: string) => {
    abort.current?.abort();
    const ctrl = new AbortController();
    abort.current = ctrl;
    setBusyId(travelerId);
    setError(null);
    // A fresh run has not been approved. Never carry a receipt across carts.
    setReceipt(null);
    setReplayNonce(0);
    setReviewing(false);
    try {
      setResult(await runRecovery(travelerId, ctrl.signal));
    } catch (e) {
      const err = e as Error;
      if (err.name !== "AbortError") setError(err.message);
    } finally {
      setBusyId(null);
    }
  }, []);

  const back = useCallback(() => {
    abort.current?.abort();
    setResult(null);
    setReceipt(null);
    setReviewing(false);
  }, []);

  /**
   * Approval is its own action. Running the pipeline drafts a message; this is
   * the only path that delivers one.
   */
  const approve = useCallback(async () => {
    if (!result) return;
    setSending(true);
    setError(null);
    try {
      setReceipt(await approveAndSend(result.travelerId));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSending(false);
    }
  }, [result]);

  const replay = useCallback(() => setReplayNonce((n) => n + 1), []);

  return (
    <div data-wf-theme={theme} className="wf-root">
      <div style={{ maxWidth: 1040, margin: "0 auto", padding: "32px 22px 96px" }}>
        <nav
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 16,
            paddingBottom: 20,
            marginBottom: 28,
            borderBottom: "var(--wf-border-hair)",
          }}
        >
          <span className="wf-serif" style={{ fontSize: 25, lineHeight: 1, color: "var(--wf-ink)" }}>
            Windfall
          </span>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            {/* Fixture mode is stated plainly and never buried. "Cached for
                reliability" must not quietly become "faked". */}
            {source === "fixture" && (
              <span
                className="wf-mono"
                style={{
                  padding: "5px 9px",
                  fontSize: 10,
                  letterSpacing: "0.09em",
                  textTransform: "uppercase",
                  borderRadius: "var(--wf-radius-sm)",
                  background: "var(--wf-amber-tint)",
                  boxShadow: "inset 0 0 0 1px var(--wf-amber-border)",
                  color: "var(--wf-amber)",
                }}
              >
                Replaying capture
              </span>
            )}
            <button
              type="button"
              onClick={toggleTheme}
              aria-label="Toggle theme"
              className="wf-mono"
              style={{
                padding: "6px 11px",
                fontSize: 10,
                letterSpacing: "0.09em",
                textTransform: "uppercase",
                border: "none",
                borderRadius: 3,
                background: "var(--wf-white)",
                boxShadow: "var(--wf-ring-rule)",
                color: "var(--wf-ink-2)",
                cursor: "pointer",
              }}
            >
              {theme === "dark" ? "Light" : "Dark"}
            </button>
          </div>
        </nav>

        {error && (
          <div
            role="alert"
            className="wf-mono"
            style={{
              marginBottom: 22,
              padding: "14px 16px",
              borderRadius: "var(--wf-radius-md)",
              background: "var(--wf-halt-tint)",
              boxShadow: "inset 0 0 0 1px var(--wf-halt)",
              fontSize: 12,
              color: "var(--wf-halt)",
            }}
          >
            {error}
          </div>
        )}

        {result && reviewing && (
          <PreviewsView
            result={result}
            onBack={() => setReviewing(false)}
            receipt={receipt}
            sending={sending}
            onApprove={approve}
          />
        )}

        {result && !reviewing && (
          <PipelineView
            result={result}
            onBack={back}
            onReview={() => setReviewing(true)}
            replayNonce={replayNonce}
            onReplay={replay}
          />
        )}

        {!result && <BrowseView queue={queue} busyId={busyId} onSelect={select} />}
      </div>
    </div>
  );
}
