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
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { BrowseView, PipelineView, PreviewsView } from "@/components/windfall";
import { WaveFooter } from "@/components/windfall/WaveFooter";
import { approveAndSend, fetchQueue, runRecovery } from "@/lib/windfall/api";
import type { QueueEntry, RecoveryResult, SendReceipt } from "@/lib/windfall/types";

export default function RecoveryConsole() {
  const [queue, setQueue] = useState<QueueEntry[]>([]);
  const [source, setSource] = useState<string>("live");
  /* Which half is replayed: prices always, reasoning only when Gemini is off. */
  const [inference, setInference] = useState<string>("");
  const [result, setResult] = useState<RecoveryResult | null>(null);
  /* Which screen is showing. Derived from `result` for browse-vs-run, and
     from this flag for the step after the trace completes. */
  const [reviewing, setReviewing] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [receipt, setReceipt] = useState<SendReceipt | null>(null);
  const [sending, setSending] = useState(false);
  const [replayNonce, setReplayNonce] = useState(0);
  /* Light by default, matching the landing page so moving between the two
     does not flip the palette. The reference console opens dark, but both
     themes are complete and the toggle is one click; a saved preference
     still wins over this default. */
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const abort = useRef<AbortController | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    fetchQueue(ctrl.signal)
      .then((r) => {
        setQueue(r.queue);
        setSource(r.source);
        setInference(r.inference ?? "");
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
      /* storage unavailable; the dark default is fine */
    }
  }, []);

  const pickTheme = useCallback((next: "light" | "dark") => {
    setTheme(next);
    try {
      localStorage.setItem("wf-theme", next);
    } catch {
      /* non-fatal */
    }
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

  /* Which stepper dot is lit: browse → pipeline → previews. */
  const step = result ? (reviewing ? 3 : 2) : 1;

  return (
    <div data-wf-theme={theme} className="wf-root">
      {/* The reference console's fixed bar: lockup → stepper → theme control. */}
      <nav className="wf-console-nav">
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 20,
            maxWidth: 1040,
            margin: "0 auto",
            padding: "12px 22px",
            boxSizing: "border-box",
          }}
        >
          {/* The lockup links to the landing page, as the handoff specifies. */}
          <Link
            href="/"
            style={{ display: "flex", alignItems: "center", gap: 11, flex: "0 0 auto", textDecoration: "none" }}
          >
            <span
              aria-hidden
              style={{
                display: "block",
                width: 28,
                height: 28,
                backgroundImage: `url(/windfall/brand/windfall-mark-${theme === "dark" ? "paper" : "ink"}.svg)`,
                backgroundSize: "contain",
                backgroundRepeat: "no-repeat",
              }}
            />
            <span className="wf-serif" style={{ fontSize: 25, lineHeight: 1, color: "var(--wf-ink)" }}>
              Windfall
            </span>
          </Link>

          <div className="wf-steps" style={{ display: "flex", alignItems: "center", justifyContent: "center", flex: "1 1 auto", minWidth: 0 }}>
            {(
              [
                [1, "Carts"],
                [2, "Pipeline"],
                [3, "Previews"],
              ] as const
            ).map(([n, label]) => (
              <div key={n} style={{ display: "flex", alignItems: "center", minWidth: 0 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
                  <span
                    className="wf-mono"
                    style={{
                      width: 26,
                      height: 26,
                      flex: "0 0 auto",
                      borderRadius: "50%",
                      display: "inline-flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontWeight: 700,
                      fontSize: 12,
                      background: n === step ? "var(--wf-ink)" : "var(--wf-surface)",
                      color: n === step ? "var(--wf-paper)" : "var(--wf-ink-3)",
                      boxShadow: n === step ? "none" : "var(--wf-ring-border)",
                    }}
                  >
                    {n}
                  </span>
                  <span
                    className="wf-eyebrow"
                    style={{ color: n === step ? "var(--wf-ink)" : "var(--wf-ink-3)", whiteSpace: "nowrap" }}
                  >
                    {label}
                  </span>
                </div>
                {n < 3 && (
                  <span aria-hidden style={{ width: 34, height: 1, flex: "0 0 auto", margin: "0 12px", background: "var(--wf-rule)" }} />
                )}
              </div>
            ))}
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 12, flex: "0 0 auto" }}>
            {/* Fixture mode is stated plainly and never buried. "Cached for
                reliability" must not quietly become "faked" -- and when the
                agents really are running over replayed prices, the badge says
                PRICES rather than claiming the whole run is a replay. */}
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
                {inference === "gemini" ? "Replaying prices · live agents" : "Replaying capture"}
              </span>
            )}
            <div
              role="group"
              aria-label="Colour theme"
              style={{
                display: "flex",
                alignItems: "center",
                padding: 3,
                borderRadius: "var(--wf-radius-sm)",
                background: "var(--wf-white)",
                boxShadow: "var(--wf-ring-rule)",
              }}
            >
              {(["dark", "light"] as const).map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => pickTheme(t)}
                  aria-pressed={theme === t}
                  className="wf-mono"
                  style={{
                    height: 26,
                    padding: "0 11px",
                    border: "none",
                    borderRadius: 3,
                    background: theme === t ? "var(--wf-ink)" : "transparent",
                    color: theme === t ? "var(--wf-paper)" : "var(--wf-ink-3)",
                    fontSize: 10,
                    letterSpacing: "0.09em",
                    textTransform: "uppercase",
                    cursor: "pointer",
                    transition: "background .15s ease, color .15s ease",
                  }}
                >
                  {t === "dark" ? "Dark" : "Light"}
                </button>
              ))}
            </div>
          </div>
        </div>
      </nav>

      <div style={{ maxWidth: 1040, margin: "0 auto", padding: "28px 22px 96px" }}>

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
      <WaveFooter variant="console" />
    </div>
  );
}
