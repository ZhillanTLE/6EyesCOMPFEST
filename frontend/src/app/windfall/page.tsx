"use client";

/**
 * The Windfall landing page -- the argument, where /recovery is the tool.
 *
 * Two deliberate departures from the design handoff, both required by the
 * claims-discipline rule in CLAUDE.md:
 *
 *  1. The prototype's stat rail led with "32% recovered with zero discount"
 *     and the carousel with "68% offered / 32% purposely declined". Nothing
 *     measured those. With six seeded carts a percentage is noise, so every
 *     figure here is a count taken from the captured run, or a statement of
 *     mechanism.
 *  2. "IDR 0 margin conceded" survives verbatim, because it is true across
 *     every outcome by construction and a test asserts it.
 *
 * The page is static: no fetch, no server data. It states how the system
 * decides, and the console is where a decision actually gets made.
 */
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useReveal } from "./reveal";

const AGENTS = [
  {
    name: "Classifier Agent",
    model: "gemini",
    body: "Reads the booking history and reasons about who this traveler is — which spending tier they sit in, and whether price is what stopped them.",
  },
  {
    name: "Searcher Agent",
    model: "gemini + mcp",
    body: "Walks the rebuild ladder through the four MCP tools, testing each attempt against the tier threshold and stopping at the first that clears.",
  },
  {
    name: "Notification Curator Agent",
    model: "gemini",
    body: "Drafts the email and the WhatsApp message in Indonesian, stating the decision that was taken rather than manufacturing urgency.",
  },
] as const;

const RUNGS = [
  { n: "01", name: "Re-price", body: "Nothing changes. The same cart is re-queried at today's price." },
  { n: "02", name: "Lateral", body: "A comparable hotel at the same star rating, same dates, same area. The flight never moves." },
  { n: "03", name: "Tier-down", body: "One star lower. Destination and dates unchanged." },
] as const;

const TRACE_ROLES = [
  { who: "The analyst", body: "decides. Nothing is delivered without an explicit approval click on the drafted message." },
  { who: "The partner", body: "audits. Every attempt the ladder tried, and what it cost, is on the record — including the ones that failed." },
  { who: "Marketing", body: "owns tone. The decision is made before the model writes; the model only writes the prose." },
  { who: "The traveler", body: "can reply. The message states what changed and why, so a wrong read is answerable." },
] as const;

/* Counts, not percentages. Every number below is what the captured six-cart
   run actually produced; `npm run build` does not check that, so if the seed
   changes these change with it. */
const FACTS = [
  { fig: "2 of 6", body: "seeded carts are sent a reminder with no offer at all — price was never what stopped them." },
  { fig: "IDR 0", body: "margin conceded, on every outcome. A rebuilt cart is cheaper because the trip changed, not because anyone discounted." },
  { fig: "1", body: "request cycle. The whole trace — classification, every ladder attempt, the drafted message — returns in one response." },
] as const;

function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <div className="wf-eyebrow" style={{ marginBottom: 14 }}>
      {children}
    </div>
  );
}

function Band({
  id,
  alt = false,
  children,
}: {
  id?: string;
  alt?: boolean;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className={alt ? "wf-band-alt" : "wf-band"}>
      <div className="wf-band-inner">{children}</div>
    </section>
  );
}

export default function WindfallLanding() {
  const [theme, setTheme] = useState<"light" | "dark">("light");
  useReveal();

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

  const cta: React.CSSProperties = {
    display: "inline-flex",
    alignItems: "center",
    gap: 9,
    padding: "14px 24px",
    fontSize: 14,
    fontWeight: 600,
    borderRadius: "var(--wf-radius-md)",
    background: "var(--wf-ink)",
    color: "var(--wf-paper)",
    textDecoration: "none",
  };

  return (
    <div data-wf-theme={theme}>
      <nav
        style={{
          position: "sticky",
          top: 0,
          zIndex: 10,
          background: "var(--wf-paper)",
          borderBottom: "var(--wf-border-hair)",
        }}
      >
        <div
          style={{
            maxWidth: 1040,
            margin: "0 auto",
            padding: "14px 22px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 16,
          }}
        >
          <span className="wf-serif" style={{ fontSize: 25, lineHeight: 1, color: "var(--wf-ink)" }}>
            Windfall
          </span>
          <div style={{ display: "flex", alignItems: "center", gap: 18, flexWrap: "wrap" }}>
            <a href="#decision" style={{ fontSize: 13, color: "var(--wf-ink-2)", textDecoration: "none" }}>
              The decision
            </a>
            <a href="#ladder" style={{ fontSize: 13, color: "var(--wf-ink-2)", textDecoration: "none" }}>
              The ladder
            </a>
            <a href="#trace" style={{ fontSize: 13, color: "var(--wf-ink-2)", textDecoration: "none" }}>
              The trace
            </a>
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
            <Link href="/recovery" className="wf-mono" style={{ fontSize: 13, fontWeight: 700, color: "var(--wf-ink)", textDecoration: "none" }}>
              Console &rarr;
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <Band>
        <h1 className="wf-display" data-reveal style={{ maxWidth: "16ch" }}>
          Rebuild the cart.<br />Don&rsquo;t discount it.
        </h1>
        <p
          data-reveal
          data-reveal-delay="80"
          style={{
            margin: "22px 0 0",
            maxWidth: "56ch",
            fontSize: 16,
            lineHeight: 1.65,
            color: "var(--wf-ink-2)",
          }}
        >
          Windfall is abandoned-cart recovery for online travel agencies. Three
          agents read the traveler&rsquo;s history, work out whether price was
          ever the obstacle, and rebuild the trip to fit them — or deliberately
          send nothing at all.
        </p>
        <div data-reveal data-reveal-delay="120" style={{ marginTop: 30 }}>
          <Link href="/recovery" style={cta}>
            Rebuild carts now.
          </Link>
        </div>
      </Band>

      {/* Fact rail. The restraint metrics, stated as counts. */}
      <Band alt>
        <Eyebrow>By construction, from the captured run</Eyebrow>
        <div
          className="wf-cols"
          style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 30 }}
        >
          {FACTS.map((f, i) => (
            <div key={f.fig} data-reveal data-reveal-delay={String(i * 80)}>
              <div
                className="wf-mono"
                style={{ fontSize: 34, fontWeight: 700, letterSpacing: "-0.02em", color: "var(--wf-ink)" }}
              >
                {f.fig}
              </div>
              <p style={{ margin: "10px 0 0", fontSize: 14, lineHeight: 1.65, color: "var(--wf-ink-2)" }}>
                {f.body}
              </p>
            </div>
          ))}
        </div>
      </Band>

      {/* Three agents */}
      <Band>
        <Eyebrow>Three agents, in sequence</Eyebrow>
        <h2 className="wf-h2" data-reveal style={{ maxWidth: "20ch" }}>
          Each one hands the next a decision, not a guess.
        </h2>
        <div
          className="wf-cols"
          style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 26, marginTop: 40 }}
        >
          {AGENTS.map((a, i) => (
            <div
              key={a.name}
              data-reveal
              data-reveal-delay={String(i * 80)}
              style={{
                padding: "22px 20px",
                borderRadius: "var(--wf-radius-md)",
                background: "var(--wf-white)",
                boxShadow: "var(--wf-ring-border)",
              }}
            >
              <span
                aria-hidden
                style={{
                  display: "block",
                  width: 40,
                  height: 40,
                  marginBottom: 14,
                  backgroundImage: `url(/windfall/agents/${
                    i === 0 ? "classifier" : i === 1 ? "searcher" : "notifier"
                  }-awake.svg)`,
                  backgroundSize: "contain",
                  backgroundRepeat: "no-repeat",
                }}
              />
              <div style={{ fontSize: 14, fontWeight: 600, color: "var(--wf-ink)" }}>{a.name}</div>
              <div className="wf-eyebrow" style={{ marginTop: 5 }}>{a.model}</div>
              <p style={{ margin: "12px 0 0", fontSize: 13.5, lineHeight: 1.65, color: "var(--wf-ink-2)" }}>
                {a.body}
              </p>
            </div>
          ))}
        </div>
      </Band>

      {/* The decision */}
      <Band id="decision" alt>
        <Eyebrow>The decision</Eyebrow>
        <h2 className="wf-h2" data-reveal style={{ maxWidth: "22ch" }}>
          Two signals have to agree before anyone is offered anything.
        </h2>
        <div
          className="wf-cols"
          style={{ display: "grid", gridTemplateColumns: "1.05fr 1fr", gap: 34, marginTop: 40, alignItems: "start" }}
        >
          <div data-reveal>
            <pre
              className="wf-mono"
              style={{
                margin: 0,
                padding: "20px 22px",
                borderRadius: "var(--wf-radius-md)",
                background: "var(--wf-white)",
                boxShadow: "var(--wf-ring-border)",
                fontSize: 13,
                lineHeight: 1.85,
                color: "var(--wf-ink-2)",
                overflowX: "auto",
              }}
            >{`c  = campaign share    past spend on discounted product
g  = (p₀ − s) / s     how far the cart sits above
                      what this traveler usually pays

rebuild ladder   if  c ≥ 0,25  AND  g > 0
reminder         otherwise`}</pre>
          </div>
          <div data-reveal data-reveal-delay="90">
            <p style={{ margin: 0, fontSize: 14.5, lineHeight: 1.7, color: "var(--wf-ink-2)" }}>
              A high campaign share on its own never triggers an intervention.
              Neither does a cart merely being expensive. Someone who waits for
              promotions but whose cart already sits inside their usual spend is
              not blocked by price, and discounting them buys nothing that was
              not already coming.
            </p>
            <p style={{ margin: "16px 0 0", fontSize: 14.5, lineHeight: 1.7, color: "var(--wf-ink-2)" }}>
              Two of the six seeded carts resolve this way. They get a reminder
              and no offer — which is a decision the system defends, not a case
              it failed to handle.
            </p>
          </div>
        </div>
      </Band>

      {/* The ladder */}
      <Band id="ladder">
        <Eyebrow>The rebuild ladder</Eyebrow>
        <h2 className="wf-h2" data-reveal style={{ maxWidth: "24ch" }}>
          Smallest change first. Stop at the first one that clears.
        </h2>
        <p
          data-reveal
          style={{ margin: "20px 0 0", maxWidth: "60ch", fontSize: 15, lineHeight: 1.7, color: "var(--wf-ink-2)" }}
        >
          Each attempt is measured against the threshold for the traveler&rsquo;s
          tier — Value 5%, Comfort 10%, Premium 15%. The ladder stops at the
          first attempt to clear it, so what the traveler is offered stays as
          close to the trip they chose as the saving allows.
        </p>
        <div style={{ marginTop: 34, display: "flex", flexDirection: "column" }}>
          {RUNGS.map((r, i) => (
            <div
              key={r.n}
              data-reveal
              data-reveal-delay={String(i * 80)}
              style={{
                display: "flex",
                gap: 20,
                padding: "20px 0",
                borderTop: "var(--wf-border-hair)",
              }}
            >
              <span className="wf-mono" style={{ fontSize: 13, color: "var(--wf-ink-3)", flexShrink: 0 }}>
                {r.n}
              </span>
              <div>
                <div style={{ fontSize: 15, fontWeight: 600, color: "var(--wf-ink)" }}>{r.name}</div>
                <p style={{ margin: "6px 0 0", fontSize: 13.5, lineHeight: 1.65, color: "var(--wf-ink-2)" }}>
                  {r.body}
                </p>
              </div>
            </div>
          ))}
          <p
            data-reveal
            className="wf-mono"
            style={{
              margin: 0,
              padding: "20px 0 0",
              borderTop: "var(--wf-border-hair)",
              fontSize: 12.5,
              lineHeight: 1.75,
              color: "var(--wf-ink-3)",
            }}
          >
            The flight never changes. A Hold Order is held against one specific
            flight offer, so swapping it would void the price guarantee.
          </p>
        </div>
      </Band>

      {/* Relationships to the trace */}
      <Band id="trace" alt>
        <Eyebrow>Who reads the trace</Eyebrow>
        <h2 className="wf-h2" data-reveal style={{ maxWidth: "22ch" }}>
          Four relationships to one reasoning trace.
        </h2>
        <div
          className="wf-cols"
          style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 26, marginTop: 40 }}
        >
          {TRACE_ROLES.map((r, i) => (
            <div
              key={r.who}
              data-reveal
              data-reveal-delay={String(i * 70)}
              style={{
                padding: "20px 22px",
                borderRadius: "var(--wf-radius-md)",
                background: "var(--wf-paper)",
                boxShadow: "var(--wf-ring-border)",
              }}
            >
              <p style={{ margin: 0, fontSize: 14.5, lineHeight: 1.7, color: "var(--wf-ink-2)" }}>
                <strong style={{ color: "var(--wf-ink)", fontWeight: 600 }}>{r.who}</strong> {r.body}
              </p>
            </div>
          ))}
        </div>
      </Band>

      {/* Closing CTA */}
      <Band>
        <div data-reveal style={{ textAlign: "center" }}>
          <h2 className="wf-h2" style={{ maxWidth: "20ch", margin: "0 auto" }}>
            Six carts. Six decisions. One of them is to do nothing.
          </h2>
          <p
            style={{
              margin: "20px auto 0",
              maxWidth: "52ch",
              fontSize: 15,
              lineHeight: 1.7,
              color: "var(--wf-ink-2)",
            }}
          >
            The console ships with a captured run, so it works with no keys and
            no network. Open it and compare the two Premium travelers — same
            tier, same threshold, opposite outcomes.
          </p>
          <div style={{ marginTop: 30 }}>
            <Link href="/recovery" style={cta}>
              Open the console
            </Link>
          </div>
        </div>
      </Band>

      <footer className="wf-band-ink">
        <div style={{ maxWidth: 1040, margin: "0 auto", padding: "64px 22px", textAlign: "center" }}>
          <span
            aria-hidden
            className="wf-drift"
            style={{
              display: "inline-block",
              width: 44,
              height: 44,
              backgroundImage: "url(/windfall/brand/windfall-mark-paper.svg)",
              backgroundSize: "contain",
              backgroundRepeat: "no-repeat",
              backgroundPosition: "center",
            }}
          />
          <div className="wf-serif" style={{ marginTop: 14, fontSize: 25, lineHeight: 1 }}>
            Windfall
          </div>
          <p className="wf-mono" style={{ margin: "12px 0 0", fontSize: 11.5, opacity: 0.72 }}>
            COMPFEST 18 AIC &middot; Team 6 Eyes
          </p>
        </div>
      </footer>
    </div>
  );
}
