"use client";

/**
 * The Windfall landing page — the argument, where /recovery is the tool.
 *
 * Layout, motion and copy follow the reference design
 * (docs/design-plan.md maps every section). Departures, all required by
 * CLAUDE.md:
 *
 *  1. Claims discipline. The design's "32% recovered with zero discount",
 *     "68% offered / 32% declined", "62% carts abandoned" and "IDR 40jt avg
 *     cart" were never measured. Every figure on this page is a count taken
 *     from the captured ten-cart run (see backend/recovery/seed/golden.json)
 *     or a statement of mechanism. "IDR 0 margin conceded" survives verbatim
 *     because it is true across every outcome and a test asserts it.
 *  2. The pipeline demo drops the design's fake browser chrome
 *     (`BrowserFrame` is on the do-not-build list) and shows Ria Lavenia's
 *     captured run: real ledger figures, real per-stage durations, the real
 *     drafted email. It is a replay of recorded data, not inference.
 *  3. The Searcher card states the tiered thresholds, not the design's flat
 *     "≥ 3%" — the frozen constants win.
 *
 * The page is static: no fetch, no server data.
 */
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { WaveFooter } from "@/components/windfall/WaveFooter";
import { useReveal } from "./reveal";

/* ---------------------------------------------------------------- data --
   Everything below is transcribed from the captured run in
   backend/recovery/seed/golden.json. If the seed changes, these change. */

type Tag = "REBUILT" | "LATERAL" | "REMINDER" | "ALTERNATIVE" | "SKIPPED";

const TAG_TINT: Record<Tag, { ink: string; bg: string }> = {
  REBUILT: { ink: "var(--wf-signal)", bg: "var(--wf-signal-tint)" },
  LATERAL: { ink: "var(--wf-signal)", bg: "var(--wf-signal-tint)" },
  REMINDER: { ink: "var(--wf-ink-2)", bg: "var(--wf-warm)" },
  ALTERNATIVE: { ink: "var(--wf-amber)", bg: "var(--wf-amber-tint)" },
  SKIPPED: { ink: "var(--wf-halt)", bg: "var(--wf-halt-tint)" },
};

const MARQUEE: { name: string; route: string; tag: Tag; figure: string; note: string }[] = [
  { name: "Ria Lavenia", route: "HND → SIN", tag: "REBUILT", figure: "−11,2%", note: "saves 766.080 · hotel one star down" },
  { name: "Zhillan Baniaksa", route: "GRU → LIS", tag: "REBUILT", figure: "−12,6%", note: "saves 4.757.760 · hotel one star down" },
  { name: "Nasywa Namira", route: "DXB → LHR", tag: "REMINDER", figure: "IDR 0", note: "campaign share 9% · margin kept" },
  { name: "Adriano Goran", route: "BLR → DXB", tag: "ALTERNATIVE", figure: "−14,3%", note: "cold start · different trip fits" },
  { name: "Zayyan Ramadzaki", route: "ACC → LHR", tag: "LATERAL", figure: "−10,8%", note: "saves 3.758.400 · same-star swap" },
  { name: "Christiano Hosea", route: "PVG → NRT", tag: "SKIPPED", figure: "—", note: "inventory unavailable · no send" },
  { name: "Micguel Katili", route: "FCO → JFK", tag: "REBUILT", figure: "−8,7%", note: "saves 508.950 · hotel one star down" },
  { name: "Salsabilla Hasan", route: "SCL → MAD", tag: "REMINDER", figure: "IDR 0", note: "campaign share 11% · margin kept" },
  { name: "Darius Sagala", route: "LOS → ADD", tag: "ALTERNATIVE", figure: "−20,3%", note: "saves 6.763.960 · different trip" },
  { name: "Tania Ju", route: "NRT → HNL", tag: "REBUILT", figure: "−10,2%", note: "saves 871.080 · hotel one star down" },
];

/* Ria Lavenia (wf-01): the demo cart. Durations are the run's measured
   per-stage wall clock; the ledger rows are its actual attempts. */
const DEMO = {
  classifierMs: 1800,
  searcherMs: 3100,
  notifierMs: 1550,
  classifier: ["→ Campaign share 46,0% — price-sensitive", "→ Cart 14,0% above usual spend"],
  tier: "Value",
  threshold: "THRESHOLD ≥ 5%",
  ledger: [
    { n: "01", label: "Same cart, re-priced", total: "6.696.360", delta: "−2,1%", cleared: false },
    { n: "02", label: "Same-star hotel swap, same area", total: "6.580.080", delta: "−3,8%", cleared: false },
    { n: "03", label: "Hotel down one star, same area", total: "6.073.920", delta: "−11,2%", cleared: true },
  ],
  ledgerFooterL: "Value tier threshold ≥ 5,0%",
  ledgerFooterR: "Stopped at attempt 03",
  notifier: ["→ Tone tuned to the tier, leads with the rebuild", "→ States what changed, no invented urgency"],
  recon: {
    sub: "Hotel down one star, same area and dates",
    oldTotal: "IDR 6.840.000",
    newTotal: "IDR 6.073.920",
    line: "−11,2% · saves 766.080",
  },
  email: {
    subject: "Perjalanan Singapore Anda, disusun ulang agar pas",
    body:
      "Kami menyusun ulang satu bagian saja agar totalnya IDR 766.080 lebih ringan: penerbangan, tanggal, dan kawasannya tetap sama, yang berubah hanya penginapannya menjadi Hotel Boss (3 bintang).",
    old: "6.840.000",
    nw: "6.073.920",
    save: "Save IDR 766.080",
    pct: "−11,2%",
    cta: "Lihat perjalanan yang disusun ulang",
    closing: "Jika yang semula tetap yang Anda inginkan, versi itu masih utuh dan bisa Anda pilih kembali kapan saja.",
  },
};

const AGENT_CARDS = [
  {
    icon: "classifier",
    n: "01",
    name: "Classifier",
    body: "Reads the booking history, sets the tier, and states the two signals in plain lines an analyst can argue with.",
    foot: "Tier · campaign share · spend gap",
  },
  {
    icon: "searcher",
    n: "02",
    name: "Searcher",
    body: "Walks the rebuild ladder — re-price, same-star swap, one star down — and stops at the first attempt that clears the tier threshold.",
    foot: "Value 5% · Comfort 10% · Premium 15%",
  },
  {
    icon: "notifier",
    n: "03",
    name: "Notifier",
    body: "Drafts the email and the WhatsApp message for the decision that was actually made, with no invented deadlines.",
    foot: "Email + WhatsApp · approval required",
  },
] as const;

const SEGMENTS = [
  {
    num: "01",
    name: "Flight OTAs",
    why: "High volume, thin margin per ticket, so a discount aimed at the wrong traveler is felt immediately.",
    stat: "thin margins",
  },
  {
    num: "02",
    name: "Full-service airlines",
    why: "Graded cabins mean “comparable” can be defined precisely instead of guessed.",
    stat: "graded cabins",
  },
  {
    num: "03",
    name: "Hotel groups & packagers",
    why: "Flight and stay in one cart: two partner margins to protect in a single decision.",
    stat: "two margins, one cart",
  },
];

const WATCHERS = [
  { role: "The analyst decides", does: "Approves or rejects each send; the agents only propose" },
  {
    role: "The partner sees why",
    does: "When an OTA asks why an offer was or was not made, the reasoning trace answers, per cart, on the record",
  },
  { role: "Marketing owns tone", does: "Message wording and channel are editable; the decision itself is not" },
  {
    role: "The traveler can reply",
    does: "The message states what changed and why, so a wrong read is answerable rather than final",
  },
];

/* ------------------------------------------------------------- helpers -- */

const mono = (extra: React.CSSProperties = {}): React.CSSProperties => ({
  fontFamily: "var(--wf-font-mono)",
  ...extra,
});

const eyebrow = (extra: React.CSSProperties = {}): React.CSSProperties =>
  mono({
    fontSize: 10.5,
    letterSpacing: "0.09em",
    textTransform: "uppercase",
    color: "var(--wf-ink-3)",
    ...extra,
  });

function AgentDot({ agent, done, size = 34 }: { agent: string; done: boolean; size?: number }) {
  return (
    <span
      aria-hidden
      style={{
        position: "relative",
        display: "block",
        width: size,
        height: size,
        border: "1px solid var(--wf-rule)",
        borderRadius: "50%",
        background: "var(--wf-surface)",
        boxSizing: "border-box",
        overflow: "hidden",
        flex: "none",
      }}
    >
      {(["awake", "finished"] as const).map((state) => (
        <span
          key={state}
          style={{
            position: "absolute",
            inset: 3,
            backgroundImage: `url(/windfall/agents/${agent}-${state}.svg)`,
            backgroundSize: "contain",
            backgroundRepeat: "no-repeat",
            backgroundPosition: "center",
            opacity: state === "finished" ? (done ? 1 : 0) : 1,
            transition: "opacity .4s ease",
          }}
        />
      ))}
    </span>
  );
}

/* ------------------------------------------------------- pipeline demo --
   A replay of Ria Lavenia's captured run at the pace the server measured.
   Starts when scrolled into view; RUN AGAIN restarts it. */

function PipelineDemo() {
  const [phase, setPhase] = useState(0); // 0 idle · 1 classifying · 2 searching · 3 drafting · 4 done
  const [rows, setRows] = useState(0);
  const timers = useRef<number[]>([]);
  const frame = useRef<HTMLDivElement | null>(null);
  const started = useRef(false);

  const run = useCallback(() => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
    setPhase(1);
    setRows(0);
    const at = (ms: number, fn: () => void) => timers.current.push(window.setTimeout(fn, ms));
    const { classifierMs, searcherMs, notifierMs, ledger } = DEMO;
    at(classifierMs, () => setPhase(2));
    ledger.forEach((_, i) =>
      at(classifierMs + Math.round(((i + 1) * searcherMs) / (ledger.length + 1)), () => setRows(i + 1)),
    );
    at(classifierMs + searcherMs, () => setPhase(3));
    at(classifierMs + searcherMs + notifierMs, () => setPhase(4));
  }, []);

  useEffect(() => {
    const el = frame.current;
    if (!el) return;
    if (!("IntersectionObserver" in window)) {
      if (!started.current) {
        started.current = true;
        run();
      }
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting) && !started.current) {
          started.current = true;
          run();
          io.disconnect();
        }
      },
      { threshold: 0.25 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [run]);

  useEffect(() => () => timers.current.forEach(clearTimeout), []);

  const dim = (from: number): React.CSSProperties => ({
    opacity: phase >= from ? 1 : 0.16,
    transform: phase >= from ? "none" : "translateY(8px)",
    transition: "opacity .45s ease, transform .45s cubic-bezier(.22,.61,.36,1)",
  });
  const dur = (ms: number) => `${(ms / 1000).toFixed(2).replace(".", ",")}s`;

  return (
    <div
      ref={frame}
      data-reveal
      style={{
        marginTop: 40,
        border: "var(--wf-border-frame)",
        borderRadius: "var(--wf-radius-lg)",
        background: "var(--wf-white)",
        boxShadow: "var(--wf-shadow-card)",
        overflow: "hidden",
      }}
    >
      {/* Provenance bar, in place of the design's fake browser chrome. */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
          padding: "10px 14px",
          borderBottom: "var(--wf-border-hair)",
          background: "var(--wf-surface)",
        }}
      >
        <span style={eyebrow()}>From the captured run &middot; Ria Lavenia &middot; HND → SIN</span>
        <button
          type="button"
          onClick={run}
          style={mono({
            fontSize: 10.5,
            letterSpacing: "0.09em",
            color: "var(--wf-ink)",
            background: "var(--wf-white)",
            border: "var(--wf-border-frame)",
            borderRadius: "var(--wf-radius-sm)",
            padding: "5px 10px",
            cursor: "pointer",
          })}
        >
          {phase > 0 && phase < 4 ? "RUNNING…" : "RUN AGAIN"}
        </button>
      </div>

      <div className="wf-cols" style={{ display: "grid", gridTemplateColumns: "1.08fr 1fr" }}>
        {/* Left: the reasoning timeline. */}
        <div
          style={{
            padding: 24,
            borderRight: "var(--wf-border-hair)",
            display: "flex",
            flexDirection: "column",
            gap: 16,
          }}
        >
          <span style={eyebrow()}>Agent reasoning</span>

          {/* Classifier */}
          <div style={{ display: "flex", gap: 12 }}>
            <span style={{ display: "flex", flexDirection: "column", alignItems: "center", flex: "none" }}>
              <AgentDot agent="classifier" done={phase >= 2} />
              <span style={{ flex: 1, width: 1, background: "var(--wf-rule)", marginTop: 6 }} />
            </span>
            <div style={{ flex: 1, minWidth: 0, ...dim(1) }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 13.5, fontWeight: 500 }}>Classifier</span>
                <span style={eyebrow({ fontSize: 9.5, border: "var(--wf-border-hair)", borderRadius: "var(--wf-radius-sm)", padding: "2px 6px" })}>
                  GEMINI
                </span>
                <span style={mono({ marginLeft: "auto", fontSize: 11, color: "var(--wf-ink-3)" })}>
                  {phase >= 2 ? dur(DEMO.classifierMs) : ""}
                </span>
              </div>
              <div style={mono({ display: "flex", flexDirection: "column", gap: 7, marginTop: 9, fontSize: 11.5, lineHeight: 1.6, color: "var(--wf-ink-2)" })}>
                {DEMO.classifier.map((l) => (
                  <span key={l}>{l}</span>
                ))}
              </div>
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 10,
                  marginTop: 11,
                  boxShadow: "var(--wf-ring-ink)",
                  borderRadius: "var(--wf-radius-md)",
                  padding: "7px 11px",
                }}
              >
                <span style={eyebrow({ fontSize: 10 })}>Tier</span>
                <span style={{ fontSize: 14, fontWeight: 500, lineHeight: 1 }}>{DEMO.tier}</span>
                <span style={{ width: 1, height: 14, background: "var(--wf-rule)" }} />
                <span style={eyebrow({ fontSize: 10 })}>{DEMO.threshold}</span>
              </span>
            </div>
          </div>

          {/* Searcher */}
          <div style={{ display: "flex", gap: 12 }}>
            <span style={{ display: "flex", flexDirection: "column", alignItems: "center", flex: "none" }}>
              <AgentDot agent="searcher" done={phase >= 3} />
              <span style={{ flex: 1, width: 1, background: "var(--wf-rule)", marginTop: 6 }} />
            </span>
            <div style={{ flex: 1, minWidth: 0, ...dim(2) }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 13.5, fontWeight: 500 }}>Searcher</span>
                <span style={eyebrow({ fontSize: 9.5, border: "var(--wf-border-hair)", borderRadius: "var(--wf-radius-sm)", padding: "2px 6px" })}>
                  GEMINI + MCP
                </span>
                <span style={mono({ marginLeft: "auto", fontSize: 11, color: "var(--wf-ink-3)" })}>
                  {phase >= 3 ? dur(DEMO.searcherMs) : ""}
                </span>
              </div>
              <div style={mono({ display: "block", marginTop: 9, border: "var(--wf-border-hair)", borderRadius: "var(--wf-radius-md)", overflow: "hidden", fontSize: 11 })}>
                <span
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr auto auto auto",
                    gap: 12,
                    padding: "7px 11px",
                    background: "var(--wf-surface)",
                    letterSpacing: "0.09em",
                    fontSize: 9.5,
                    color: "var(--wf-ink-3)",
                  }}
                >
                  <span>ATTEMPT</span>
                  <span style={{ textAlign: "right" }}>TOTAL</span>
                  <span style={{ textAlign: "right" }}>DIFF</span>
                  <span style={{ textAlign: "right" }}>STATUS</span>
                </span>
                {DEMO.ledger.slice(0, phase >= 4 ? DEMO.ledger.length : rows).map((r) => (
                  <span
                    key={r.n}
                    className="wf-fade"
                    style={{
                      display: "grid",
                      gridTemplateColumns: "1fr auto auto auto",
                      gap: 12,
                      padding: "8px 11px",
                      background: r.cleared ? "var(--wf-signal-tint)" : "var(--wf-halt-tint)",
                      borderTop: "var(--wf-border-hair)",
                      color: "var(--wf-ink-2)",
                    }}
                  >
                    <span>
                      <span style={{ color: "var(--wf-ink-3)" }}>{r.n}</span> {r.label}
                    </span>
                    <span style={{ textAlign: "right" }}>{r.total}</span>
                    <span style={{ textAlign: "right" }}>{r.delta}</span>
                    <span style={{ textAlign: "right", color: r.cleared ? "var(--wf-signal)" : "var(--wf-halt)" }}>
                      {r.cleared ? "Cleared" : "Failed"}
                    </span>
                  </span>
                ))}
                {phase >= 4 && (
                  <span
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      gap: 12,
                      padding: "8px 11px",
                      borderTop: "var(--wf-border-hair)",
                      color: "var(--wf-ink-3)",
                    }}
                  >
                    <span>{DEMO.ledgerFooterL}</span>
                    <span>{DEMO.ledgerFooterR}</span>
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Notifier */}
          <div style={{ display: "flex", gap: 12 }}>
            <AgentDot agent="notifier" done={phase >= 4} />
            <div style={{ flex: 1, minWidth: 0, ...dim(3) }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 13.5, fontWeight: 500 }}>Notifier</span>
                <span style={eyebrow({ fontSize: 9.5, border: "var(--wf-border-hair)", borderRadius: "var(--wf-radius-sm)", padding: "2px 6px" })}>
                  GEMINI
                </span>
                <span style={mono({ marginLeft: "auto", fontSize: 11, color: "var(--wf-ink-3)" })}>
                  {phase >= 4 ? dur(DEMO.notifierMs) : ""}
                </span>
              </div>
              <div style={mono({ display: "flex", flexDirection: "column", gap: 7, marginTop: 9, fontSize: 11.5, lineHeight: 1.6, color: "var(--wf-ink-2)" })}>
                {DEMO.notifier.map((l) => (
                  <span key={l}>{l}</span>
                ))}
              </div>
            </div>
          </div>

          {/* Reconciliation */}
          <div
            style={{
              marginTop: "auto",
              display: "flex",
              alignItems: "baseline",
              justifyContent: "space-between",
              gap: 12,
              paddingTop: 15,
              borderTop: "var(--wf-border-hair)",
              ...dim(4),
            }}
          >
            <span>
              <span style={eyebrow({ display: "block", fontSize: 10 })}>Reconciliation · met</span>
              <span style={{ display: "block", marginTop: 3, fontSize: 15, fontWeight: 500 }}>Rebuild approved</span>
              <span style={mono({ display: "block", fontSize: 11.5, color: "var(--wf-ink-3)" })}>{DEMO.recon.sub}</span>
            </span>
            <span style={{ textAlign: "right", whiteSpace: "nowrap" }}>
              <span style={mono({ display: "block", fontSize: 12, color: "var(--wf-ink-3)", textDecoration: "line-through" })}>
                {DEMO.recon.oldTotal}
              </span>
              <span style={mono({ display: "block", fontWeight: 500, fontSize: 20 })}>{DEMO.recon.newTotal}</span>
              <span style={mono({ display: "block", fontSize: 12, color: "var(--wf-signal)" })}>{DEMO.recon.line}</span>
            </span>
          </div>
        </div>

        {/* Right: the drafted message. */}
        <div style={{ padding: 24, display: "flex", flexDirection: "column", gap: 12, background: "var(--wf-paper)" }}>
          <span
            style={eyebrow({
              color: "var(--wf-amber)",
              background: "var(--wf-amber-tint)",
              borderRadius: "var(--wf-radius-sm)",
              padding: "3px 8px",
              alignSelf: "flex-start",
            })}
          >
            Preview only
          </span>
          <div
            style={{
              border: "var(--wf-border-hair)",
              borderRadius: 8,
              background: "var(--wf-surface)",
              overflow: "hidden",
              ...dim(4),
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 7, padding: "9px 12px" }}>
              {["var(--wf-chrome-close)", "var(--wf-chrome-min)", "var(--wf-chrome-max)"].map((c) => (
                <span key={c} style={{ width: 8, height: 8, borderRadius: "50%", background: c }} />
              ))}
              <span style={{ marginLeft: 8, fontSize: 11.5, fontWeight: 500, color: "var(--wf-ink-2)" }}>Inbox</span>
              <span style={mono({ fontSize: 11, color: "var(--wf-ink-3)" })}>&middot; 1 pesan baru</span>
            </div>
            <div style={{ margin: "0 10px 10px", border: "var(--wf-border-hair)", borderRadius: "var(--wf-radius-md)", background: "var(--wf-white)", overflow: "hidden" }}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 9,
                  padding: "11px 13px",
                  borderBottom: "var(--wf-border-hair)",
                  background: "var(--wf-surface-2)",
                }}
              >
                <span
                  aria-hidden
                  style={{
                    display: "block",
                    width: 18,
                    height: 18,
                    flex: "none",
                    backgroundImage: "url(/windfall/brand/windfall-mark-ink.svg)",
                    backgroundSize: "contain",
                    backgroundRepeat: "no-repeat",
                  }}
                />
                <span style={{ fontSize: 13, fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {DEMO.email.subject}
                </span>
              </div>
              <div style={{ padding: "14px 13px", display: "flex", flexDirection: "column", gap: 11 }}>
                <p style={{ margin: 0, fontSize: 12.5, lineHeight: 1.75, color: "var(--wf-ink)", textWrap: "pretty" }}>
                  {DEMO.email.body}
                </p>
                <div
                  style={{
                    display: "flex",
                    alignItems: "baseline",
                    justifyContent: "space-between",
                    gap: 12,
                    padding: "12px 13px",
                    borderRadius: "var(--wf-radius-md)",
                    background: "var(--wf-surface)",
                  }}
                >
                  <span style={mono({ display: "flex", alignItems: "baseline", gap: 9, whiteSpace: "nowrap" })}>
                    <span style={{ fontSize: 12, color: "var(--wf-ink-3)", textDecoration: "line-through" }}>{DEMO.email.old}</span>
                    <span style={{ fontWeight: 500, fontSize: 19 }}>{DEMO.email.nw}</span>
                  </span>
                  <span style={mono({ textAlign: "right", whiteSpace: "nowrap", fontSize: 11.5, color: "var(--wf-signal)" })}>
                    <span style={{ display: "block" }}>{DEMO.email.save}</span>
                    <span style={{ display: "block" }}>{DEMO.email.pct}</span>
                  </span>
                </div>
                <span
                  style={{
                    display: "block",
                    textAlign: "center",
                    fontSize: 12.5,
                    fontWeight: 600,
                    color: "var(--wf-cta-ink)",
                    background: "var(--wf-cta)",
                    borderRadius: "var(--wf-radius-md)",
                    padding: "12px 14px",
                  }}
                >
                  {DEMO.email.cta}
                </span>
                <span style={{ fontSize: 11.5, lineHeight: 1.6, color: "var(--wf-ink-3)", textWrap: "pretty" }}>
                  {DEMO.email.closing}
                </span>
              </div>
            </div>
          </div>
          <div
            style={{
              marginTop: "auto",
              display: "flex",
              alignItems: "baseline",
              justifyContent: "space-between",
              paddingTop: 14,
              borderTop: "var(--wf-border-hair)",
            }}
          >
            <span style={eyebrow({ fontSize: 11 })}>Sent after approval</span>
            <span style={mono({ fontSize: 12, color: "var(--wf-ink-2)" })}>email + whatsapp</span>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------- page -- */

export default function WindfallLanding() {
  useReveal();

  const inkBtn: React.CSSProperties = {
    fontSize: 14,
    fontWeight: 500,
    lineHeight: "22px",
    whiteSpace: "nowrap",
    padding: "12px 22px",
    borderRadius: "var(--wf-radius-md)",
    background: "var(--wf-ink)",
    color: "var(--wf-paper)",
    textDecoration: "none",
  };
  const outlineBtn: React.CSSProperties = {
    fontSize: 14,
    fontWeight: 500,
    lineHeight: "22px",
    whiteSpace: "nowrap",
    padding: "12px 22px",
    borderRadius: "var(--wf-radius-md)",
    border: "var(--wf-border-frame)",
    background: "var(--wf-white)",
    color: "var(--wf-ink)",
    textDecoration: "none",
  };

  return (
    /* The landing page commits to the light palette, as the reference does;
       the console keeps the theme toggle. */
    <div data-wf-theme="light" className="wf-root">
      <nav className="wf-landing-nav">
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 24,
            maxWidth: 1080,
            margin: "0 auto",
            padding: "12px 22px",
            boxSizing: "border-box",
          }}
        >
          <span style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span
              aria-hidden
              style={{
                display: "block",
                width: 26,
                height: 26,
                backgroundImage: "url(/windfall/brand/windfall-mark-ink.svg)",
                backgroundSize: "contain",
                backgroundRepeat: "no-repeat",
              }}
            />
            <span className="wf-serif" style={{ fontSize: 25, lineHeight: 1, color: "var(--wf-ink)" }}>
              Windfall
            </span>
          </span>
          <div className="wf-cols" style={{ display: "flex", alignItems: "center", gap: 28, fontSize: 13, fontWeight: 500 }}>
            {[
              ["Product", "#product"],
              ["Market", "#market"],
              ["Who runs it", "#user"],
            ].map(([label, hash]) => (
              <a key={hash} href={hash} style={{ color: "var(--wf-ink)", textDecoration: "none", whiteSpace: "nowrap" }}>
                {label}
              </a>
            ))}
          </div>
          <Link href="/recovery" className="wf-btn-ink" style={{ ...inkBtn, padding: "8px 15px", fontSize: 13, lineHeight: "20px" }}>
            Open the console
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <div style={{ background: "var(--wf-paper)" }}>
        <div style={{ maxWidth: 1080, margin: "0 auto", padding: "96px 22px 72px", boxSizing: "border-box" }}>
          <a
            href="#product"
            data-reveal
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 10,
              padding: "5px 14px 5px 5px",
              background: "var(--wf-warm)",
              borderRadius: 999,
              whiteSpace: "nowrap",
              textDecoration: "none",
            }}
          >
            <span
              style={{
                fontSize: 13,
                fontWeight: 600,
                lineHeight: 1,
                color: "var(--wf-paper)",
                background: "var(--wf-approve)",
                borderRadius: 999,
                padding: "7px 12px",
              }}
            >
              New
            </span>
            <span style={{ fontSize: 14, fontWeight: 500, lineHeight: 1, color: "var(--wf-ink)" }}>
              The three-agent pipeline is live
            </span>
            <span style={{ display: "flex", alignItems: "center" }}>
              {["classifier", "searcher", "notifier"].map((a, i) => (
                <span
                  key={a}
                  aria-hidden
                  style={{
                    display: "block",
                    width: 24,
                    height: 24,
                    borderRadius: 5,
                    marginLeft: i ? -7 : 0,
                    boxShadow: "0 0 0 2px var(--wf-warm)",
                    background: "var(--wf-white)",
                    backgroundImage: `url(/windfall/agents/${a}-awake.svg)`,
                    backgroundSize: "contain",
                    backgroundRepeat: "no-repeat",
                    backgroundPosition: "center",
                  }}
                />
              ))}
            </span>
            <span style={mono({ fontSize: 14, color: "var(--wf-ink-3)" })}>&rsaquo;</span>
          </a>

          <h1 className="wf-display" data-reveal data-reveal-delay="80" style={{ margin: "26px 0 0", maxWidth: "20ch", textWrap: "pretty" }}>
            We rebuild abandoned carts, not give discounts.
          </h1>

          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              alignItems: "flex-end",
              justifyContent: "space-between",
              gap: 28,
              marginTop: 26,
            }}
          >
            <p
              data-reveal
              data-reveal-delay="160"
              style={{ margin: 0, maxWidth: "56ch", fontSize: 16, lineHeight: 1.65, color: "var(--wf-ink-2)", textWrap: "pretty" }}
            >
              Three agents read two signals on every cart: how often the traveler waits for a promo, and how far this
              cart sits from what they usually spend. Only when both signals agree does an offer leave the building.
            </p>
            <div
              data-reveal
              data-reveal-delay="200"
              style={{ display: "flex", flexWrap: "wrap", gap: "14px 40px", paddingTop: 18, borderTop: "var(--wf-border-hair)" }}
            >
              <span>
                <span style={mono({ display: "block", fontWeight: 700, fontSize: 26, lineHeight: 1.1, letterSpacing: "-0.01em", color: "var(--wf-signal)" })}>
                  2 of 10
                </span>
                <span style={{ display: "block", marginTop: 4, fontSize: 13, lineHeight: 1.6, color: "var(--wf-ink-2)" }}>
                  seeded carts sent a reminder, no offer — on purpose
                </span>
              </span>
              <span>
                <span style={mono({ display: "block", fontWeight: 700, fontSize: 26, lineHeight: 1.1, letterSpacing: "-0.01em" })}>
                  IDR 0
                </span>
                <span style={{ display: "block", marginTop: 4, fontSize: 13, lineHeight: 1.6, color: "var(--wf-ink-2)" }}>
                  margin conceded, on every outcome
                </span>
              </span>
            </div>
            <div data-reveal data-reveal-delay="240" style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <Link href="/recovery" className="wf-btn-ink" style={inkBtn}>
                Rebuild carts now
              </Link>
              <a href="#product" className="wf-btn-outline" style={outlineBtn}>
                See the logic
              </a>
            </div>
          </div>

          {/* Decision marquee */}
          <div className="wf-mq" data-reveal style={{ marginTop: 44, position: "relative", overflow: "hidden" }}>
            <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 16, paddingBottom: 14 }}>
              <span style={mono({ fontSize: 15, lineHeight: 1.5, letterSpacing: "-0.005em", color: "var(--wf-ink-2)" })}>
                Decisions from the captured run
              </span>
              <span style={{ fontSize: 12.5, lineHeight: 1.6, color: "var(--wf-ink-2)", textAlign: "right" }}>
                7 of 10 carts got an offer. 2 were left alone on purpose. 1 was skipped on an inventory failure.
              </span>
            </div>
            <div className="wf-mq-track">
              {[...MARQUEE, ...MARQUEE].map((c, i) => (
                <div
                  key={`${c.name}-${i}`}
                  className="wf-mq-card"
                  aria-hidden={i >= MARQUEE.length}
                  style={{
                    flex: "0 0 auto",
                    display: "flex",
                    flexDirection: "column",
                    gap: 8,
                    width: 236,
                    padding: "14px 16px",
                    border: "var(--wf-border-hair)",
                    borderRadius: "var(--wf-radius-md)",
                    background: "var(--wf-white)",
                  }}
                >
                  <span style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 10 }}>
                    <span style={{ fontSize: 13, fontWeight: 500, whiteSpace: "nowrap" }}>{c.name}</span>
                    <span style={mono({ fontSize: 11, color: "var(--wf-ink-3)", whiteSpace: "nowrap" })}>{c.route}</span>
                  </span>
                  <span style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 }}>
                    <span
                      style={mono({
                        fontSize: 10,
                        letterSpacing: "0.08em",
                        color: TAG_TINT[c.tag].ink,
                        background: TAG_TINT[c.tag].bg,
                        borderRadius: "var(--wf-radius-sm)",
                        padding: "3px 7px",
                        whiteSpace: "nowrap",
                      })}
                    >
                      {c.tag}
                    </span>
                    <span style={mono({ fontSize: 12.5, whiteSpace: "nowrap" })}>{c.figure}</span>
                  </span>
                  <span style={mono({ fontSize: 11, color: "var(--wf-ink-3)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" })}>
                    {c.note}
                  </span>
                </div>
              ))}
            </div>
            <div
              aria-hidden
              style={{ position: "absolute", left: 0, bottom: 0, width: 96, height: 96, background: "linear-gradient(90deg, var(--wf-paper), transparent)", pointerEvents: "none" }}
            />
            <div
              aria-hidden
              style={{ position: "absolute", right: 0, bottom: 0, width: 96, height: 96, background: "linear-gradient(270deg, var(--wf-paper), transparent)", pointerEvents: "none" }}
            />
          </div>

          <PipelineDemo />
        </div>
      </div>

      {/* Product */}
      <div id="product" style={{ background: "var(--wf-white)", borderTop: "var(--wf-border-hair)", borderBottom: "var(--wf-border-hair)" }}>
        <div style={{ maxWidth: 1080, margin: "0 auto", padding: "88px 22px", boxSizing: "border-box" }}>
          <h2 className="wf-h2" data-reveal style={{ maxWidth: "24ch" }}>
            One console. Three agents. Nothing else.
          </h2>
          <div className="wf-cols" data-reveal style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, marginTop: 36 }}>
            {AGENT_CARDS.map((a) => (
              <div
                key={a.n}
                className="wf-lift"
                style={{
                  border: "var(--wf-border-hair)",
                  borderRadius: "var(--wf-radius-md)",
                  background: "var(--wf-paper)",
                  padding: 24,
                  display: "flex",
                  flexDirection: "column",
                  gap: 12,
                }}
              >
                <span style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 }}>
                  <span
                    aria-hidden
                    style={{
                      display: "block",
                      width: 34,
                      height: 34,
                      backgroundImage: `url(/windfall/agents/${a.icon}-awake.svg)`,
                      backgroundSize: "contain",
                      backgroundRepeat: "no-repeat",
                    }}
                  />
                  <span style={mono({ fontSize: 11, letterSpacing: "0.09em", color: "var(--wf-ink-3)" })}>{a.n}</span>
                </span>
                <h3 style={mono({ margin: 0, fontWeight: 700, fontSize: 19, letterSpacing: "-0.01em" })}>{a.name}</h3>
                <p style={{ margin: 0, fontSize: 13, lineHeight: 1.7, color: "var(--wf-ink-2)", textWrap: "pretty" }}>{a.body}</p>
                <span style={mono({ marginTop: "auto", paddingTop: 14, borderTop: "var(--wf-border-hair)", fontSize: 11.5, color: "var(--wf-ink-2)" })}>
                  {a.foot}
                </span>
              </div>
            ))}
          </div>
          <p
            data-reveal
            style={{
              margin: "16px 0 0",
              padding: "16px 20px",
              border: "1px dashed var(--wf-border)",
              borderRadius: "var(--wf-radius-md)",
              fontSize: 13,
              lineHeight: 1.7,
              color: "var(--wf-ink-2)",
            }}
          >
            <span style={mono({ fontSize: 15, lineHeight: 1.5, letterSpacing: "-0.005em", color: "var(--wf-halt)" })}>
              Not built on purpose.&nbsp;&nbsp;
            </span>
            No CRM, no pricing engine, no blast tool. Windfall answers one question per cart.
          </p>
        </div>
      </div>

      {/* Market */}
      <div id="market" style={{ background: "var(--wf-warm)" }}>
        <div style={{ maxWidth: 1080, margin: "0 auto", padding: "88px 22px", boxSizing: "border-box" }}>
          <div className="wf-cols" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 28, alignItems: "end" }}>
            <h2 className="wf-h2" data-reveal style={{ margin: 0 }}>
              Carts too valuable to discount blindly.
            </h2>
            <p data-reveal style={{ margin: 0, fontSize: 14, lineHeight: 1.75, color: "var(--wf-ink-2)", textWrap: "pretty" }}>
              Reasoning costs more than a cheap cart is worth. Windfall pays for itself where one abandoned cart is tens
              of millions of rupiah and a partner&rsquo;s margin rides on the answer.
            </p>
          </div>
          <div data-reveal style={{ marginTop: 36, borderTop: "1px solid var(--wf-border)" }}>
            {SEGMENTS.map((s) => (
              <div
                key={s.num}
                className="wf-cols wf-row-hover"
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: 16,
                  alignItems: "baseline",
                  padding: "24px 14px",
                  borderBottom: "1px solid var(--wf-warm-rule)",
                  borderRadius: "var(--wf-radius-md)",
                }}
              >
                <span style={{ display: "flex", alignItems: "baseline", gap: 16 }}>
                  <span style={mono({ fontSize: 11, letterSpacing: "0.09em", color: "var(--wf-ink-3)" })}>{s.num}</span>
                  <span style={mono({ fontWeight: 700, fontSize: 23, letterSpacing: "-0.01em" })}>{s.name}</span>
                </span>
                <span style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 20 }}>
                  <span style={{ fontSize: 13, lineHeight: 1.7, color: "var(--wf-ink-2)", maxWidth: "42ch", textWrap: "pretty" }}>
                    {s.why}
                  </span>
                  <span style={mono({ fontSize: 13, whiteSpace: "nowrap" })}>{s.stat}</span>
                </span>
              </div>
            ))}
          </div>
          <p data-reveal style={mono({ margin: "18px 0 0", fontSize: 12, color: "var(--wf-ink-3)" })}>
            Not for flat-priced retail carts or single-property stays. Without tiers, &ldquo;comparable&rdquo; has no
            meaning.
          </p>
        </div>
      </div>

      {/* Who runs it */}
      <div id="user" style={{ background: "var(--wf-white)", borderTop: "var(--wf-border-hair)" }}>
        <div style={{ maxWidth: 1080, margin: "0 auto", padding: "88px 22px", boxSizing: "border-box" }}>
          <h2 className="wf-h2" data-reveal style={{ maxWidth: "30ch" }}>
            One decision, one approver, and a trace everyone else can read.
          </h2>
          <div className="wf-cols" data-reveal style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginTop: 36, alignItems: "start" }}>
            <div className="wf-lift" style={{ border: "var(--wf-border-frame)", borderRadius: "var(--wf-radius-md)", background: "var(--wf-paper)", overflow: "hidden" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 13, padding: 20, borderBottom: "var(--wf-border-hair)" }}>
                <span
                  style={mono({
                    width: 44,
                    height: 44,
                    borderRadius: "var(--wf-radius-avatar)",
                    background: "var(--wf-ink)",
                    color: "var(--wf-paper)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: 14,
                  })}
                >
                  MK
                </span>
                <span>
                  {/* Staff persona only; the name never appears in the traveler seed. */}
                  <span style={{ display: "block", fontSize: 16, fontWeight: 500 }}>Mika Kurosawa</span>
                  <span style={mono({ display: "block", fontSize: 11.5, color: "var(--wf-ink-3)" })}>
                    Revenue recovery analyst &middot; approves every send
                  </span>
                </span>
              </div>
              <div style={mono({ padding: 20, display: "flex", flexDirection: "column", gap: 10, fontSize: 12, color: "var(--wf-ink-2)" })}>
                <span>
                  <span style={{ color: "var(--wf-ink)" }}>08.40</span>&nbsp;&nbsp;opens the queue of abandoned carts
                </span>
                <span>
                  <span style={{ color: "var(--wf-ink)" }}>09.05</span>&nbsp;&nbsp;approves Ria&rsquo;s rebuild at −11,2%
                </span>
                <span>
                  <span style={{ color: "var(--wf-ink)" }}>09.11</span>&nbsp;&nbsp;reads why Nasywa got no offer: campaign share 9%
                </span>
                <span>
                  <span style={{ color: "var(--wf-ink)" }}>16.30</span>&nbsp;&nbsp;reads what came back, notes what didn&rsquo;t
                </span>
              </div>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: "12px 16px",
                  flexWrap: "wrap",
                  padding: "14px 20px",
                  background: "var(--wf-warm)",
                  borderTop: "var(--wf-border-hair)",
                }}
              >
                <span style={{ fontSize: 13, lineHeight: 1.7 }}>The agents never send on their own.</span>
                <span style={mono({ fontSize: 11, letterSpacing: "0.06em", color: "var(--wf-signal)" })}>NAMED APPROVER</span>
              </div>
            </div>
            <div style={{ display: "flex", flexDirection: "column", borderTop: "1px solid var(--wf-border)" }}>
              {WATCHERS.map((w) => (
                <div
                  key={w.role}
                  className="wf-row-hover"
                  style={{
                    display: "flex",
                    alignItems: "baseline",
                    justifyContent: "space-between",
                    gap: 18,
                    padding: "16px 12px",
                    borderBottom: "var(--wf-border-hair)",
                    borderRadius: "var(--wf-radius-sm)",
                  }}
                >
                  <span style={{ fontSize: 14, fontWeight: 500, lineHeight: 1.6, flex: "none", maxWidth: "15ch" }}>{w.role}</span>
                  <span style={{ fontSize: 13, lineHeight: 1.7, color: "var(--wf-ink-2)", textAlign: "right", textWrap: "pretty" }}>
                    {w.does}
                  </span>
                </div>
              ))}
              <p style={mono({ margin: "16px 0 0", fontSize: 15, lineHeight: 1.5, letterSpacing: "-0.005em", color: "var(--wf-ink-2)", textWrap: "pretty" })}>
                Relationships to the trace, not seats in an org chart.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Closing CTA */}
      <div style={{ background: "var(--wf-footer-ink)", color: "var(--wf-footer-paper)" }}>
        <div style={{ maxWidth: 1080, margin: "0 auto", padding: "52px 22px 56px", boxSizing: "border-box", textAlign: "center" }}>
          <span
            aria-hidden
            data-reveal
            style={{
              display: "block",
              width: 34,
              height: 34,
              margin: "0 auto 18px",
              backgroundImage: "url(/windfall/brand/windfall-mark-paper.svg)",
              backgroundSize: "contain",
              backgroundRepeat: "no-repeat",
            }}
          />
          <h2 className="wf-h2" data-reveal style={{ margin: "0 auto", maxWidth: "22ch" }}>
            Rebuild carts now and read the reasoning.
          </h2>
          <p
            data-reveal
            style={{ margin: "18px auto 0", maxWidth: "50ch", fontSize: 15, lineHeight: 1.7, color: "var(--wf-footer-mute)", textWrap: "pretty" }}
          >
            Seeded data, no integration. Five minutes tells you whether this is how your team should be deciding
            offers.
          </p>
          <Link
            href="/recovery"
            data-reveal
            className="wf-btn-ink"
            style={{
              display: "inline-block",
              marginTop: 28,
              fontSize: 14,
              fontWeight: 500,
              lineHeight: "22px",
              padding: "12px 22px",
              borderRadius: "var(--wf-radius-md)",
              whiteSpace: "nowrap",
              background: "var(--wf-footer-paper)",
              color: "var(--wf-footer-ink)",
              textDecoration: "none",
            }}
          >
            Open the console
          </Link>
        </div>
      </div>

      <WaveFooter variant="landing" />
    </div>
  );
}
