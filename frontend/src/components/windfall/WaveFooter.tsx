"use client";

/**
 * WaveFooter — the reference design's closing band, shared by the landing
 * page and the console.
 *
 * A warm rounded ground with a slow gradient tide, three drifting wave
 * layers, and the oversized "windfall" wordmark, followed by the small
 * bottom bar. The reference keeps this band light even under the dark
 * console theme, so every colour here is a theme-invariant --wf-footer-* /
 * --wf-warm-* token rather than the themed ink ramp.
 *
 * The landing variant carries the two pulse-arrow links; the console variant
 * is the three-column form the reference gives the console page.
 */
import Link from "next/link";

const WAVES = [
  {
    height: 132,
    fill: "var(--wf-wave-1)",
    dur: "46s",
    delay: "0s",
    opacity: 1,
    d: "M0 132 L0 95.04 C 60 95.04, 90 44.88, 170 44.88 C 235 44.88, 255 7.92, 330 7.92 C 405 7.92, 425 52.8, 500 52.8 C 560 52.8, 585 26.4, 660 26.4 C 740 26.4, 760 73.92, 840 73.92 C 910 73.92, 935 34.32, 1010 34.32 C 1090 34.32, 1110 81.84, 1200 95.04 L1200 95.04 C 1260 95.04, 1290 44.88, 1370 44.88 C 1435 44.88, 1455 7.92, 1530 7.92 C 1605 7.92, 1625 52.8, 1700 52.8 C 1760 52.8, 1785 26.4, 1860 26.4 C 1940 26.4, 1960 73.92, 2040 73.92 C 2110 73.92, 2135 34.32, 2210 34.32 C 2290 34.32, 2310 81.84, 2400 95.04 L2400 132 Z",
  },
  {
    height: 96,
    fill: "var(--wf-wave-2)",
    dur: "32s",
    delay: "-6s",
    opacity: 0.9,
    d: "M0 96 L0 69.12 C 60 69.12, 90 32.64, 170 32.64 C 235 32.64, 255 5.76, 330 5.76 C 405 5.76, 425 38.4, 500 38.4 C 560 38.4, 585 19.2, 660 19.2 C 740 19.2, 760 53.76, 840 53.76 C 910 53.76, 935 24.96, 1010 24.96 C 1090 24.96, 1110 59.52, 1200 69.12 L1200 69.12 C 1260 69.12, 1290 32.64, 1370 32.64 C 1435 32.64, 1455 5.76, 1530 5.76 C 1605 5.76, 1625 38.4, 1700 38.4 C 1760 38.4, 1785 19.2, 1860 19.2 C 1940 19.2, 1960 53.76, 2040 53.76 C 2110 53.76, 2135 24.96, 2210 24.96 C 2290 24.96, 2310 59.52, 2400 69.12 L2400 96 Z",
  },
  {
    height: 60,
    fill: "var(--wf-wave-3)",
    dur: "22s",
    delay: "-11s",
    opacity: 1,
    d: "M0 60 L0 43.2 C 60 43.2, 90 20.4, 170 20.4 C 235 20.4, 255 3.6, 330 3.6 C 405 3.6, 425 24, 500 24 C 560 24, 585 12, 660 12 C 740 12, 760 33.6, 840 33.6 C 910 33.6, 935 15.6, 1010 15.6 C 1090 15.6, 1110 37.2, 1200 43.2 L1200 43.2 C 1260 43.2, 1290 20.4, 1370 20.4 C 1435 20.4, 1455 3.6, 1530 3.6 C 1605 3.6, 1625 24, 1700 24 C 1760 24, 1785 12, 1860 12 C 1940 12, 1960 33.6, 2040 33.6 C 2110 33.6, 2135 15.6, 2210 15.6 C 2290 15.6, 2310 37.2, 2400 43.2 L2400 60 Z",
  },
] as const;

const mono = (extra: React.CSSProperties = {}): React.CSSProperties => ({
  fontFamily: "var(--wf-font-mono)",
  ...extra,
});

function ProductLinks({ prefix }: { prefix: string }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <span style={{ fontSize: 13, fontWeight: 500, color: "var(--wf-footer-ink)" }}>Product</span>
      {[
        ["Agents", "#product"],
        ["Market", "#market"],
        ["Who runs it", "#user"],
      ].map(([label, hash]) => (
        <a
          key={hash}
          href={`${prefix}${hash}`}
          style={{ fontSize: 13, lineHeight: 1.6, color: "var(--wf-footer-mute)", textDecoration: "none" }}
        >
          {label}
        </a>
      ))}
    </div>
  );
}

function Channels() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <span style={{ fontSize: 13, fontWeight: 500, color: "var(--wf-footer-ink)" }}>Channels</span>
      {["email", "whatsapp", "gemini + mcp"].map((c) => (
        <span key={c} style={mono({ fontSize: 12, color: "var(--wf-footer-mute)" })}>
          {c}
        </span>
      ))}
    </div>
  );
}

export function WaveFooter({ variant }: { variant: "landing" | "console" }) {
  const landing = variant === "landing";
  /* Anchors resolve in place on the landing page, which is the root route;
     the console links across to it. */
  const prefix = landing ? "" : "/";

  return (
    <div style={{ background: "var(--wf-footer-paper)" }}>
      <div
        style={{
          position: "relative",
          background: "var(--wf-warm)",
          borderRadius: "28px 28px 0 0",
          overflow: "hidden",
        }}
      >
        <div
          aria-hidden
          className="wf-tide"
          style={{
            position: "absolute",
            inset: 0,
            pointerEvents: "none",
            background:
              "radial-gradient(120% 80% at 12% 0%, rgba(255,255,255,0.9), rgba(255,255,255,0) 60%), radial-gradient(90% 70% at 88% 10%, var(--wf-tide-gold), transparent 65%)",
            backgroundSize: "180% 180%, 160% 160%",
          }}
        />
        <div
          className="wf-cols"
          style={{
            position: "relative",
            display: "grid",
            gridTemplateColumns: landing ? "1.4fr 0.9fr 0.9fr minmax(230px, 1.3fr)" : "1.6fr 1fr 1fr",
            gap: 28,
            maxWidth: 1080,
            margin: "0 auto",
            padding: "56px 22px 0",
            boxSizing: "border-box",
          }}
        >
          <p
            style={{
              margin: 0,
              fontSize: 17,
              fontWeight: 500,
              lineHeight: 1.45,
              maxWidth: "24ch",
              textWrap: "pretty",
              color: "var(--wf-footer-ink)",
            }}
          >
            Windfall decides what an abandoned cart deserves, one cart at a time.
          </p>
          <ProductLinks prefix={prefix} />
          <Channels />
          {landing && (
            <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
              <Link
                href="/recovery"
                style={{
                  display: "block",
                  paddingBottom: 14,
                  borderBottom: "1px solid var(--wf-warm-rule)",
                  textDecoration: "none",
                }}
              >
                <span style={{ display: "flex", alignItems: "center", gap: 9 }}>
                  <span style={{ fontSize: 19, fontWeight: 500, whiteSpace: "nowrap", color: "var(--wf-approve)" }}>
                    Open the console
                  </span>
                  <span
                    aria-hidden
                    className="wf-ring-pulse"
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      width: 22,
                      height: 22,
                      borderRadius: "50%",
                      background: "var(--wf-approve)",
                      color: "var(--wf-footer-paper)",
                      fontSize: 11,
                    }}
                  >
                    ↗
                  </span>
                </span>
                <span style={{ display: "block", fontSize: 13, lineHeight: 1.6, color: "var(--wf-footer-mute)" }}>
                  Run ten seeded carts
                </span>
              </Link>
              <a href="#user" style={{ display: "block", textDecoration: "none" }}>
                <span style={{ display: "flex", alignItems: "center", gap: 9 }}>
                  <span style={{ fontSize: 19, fontWeight: 500, whiteSpace: "nowrap", color: "var(--wf-footer-ink)" }}>
                    Approval trace
                  </span>
                  <span
                    aria-hidden
                    className="wf-ring-pulse"
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      width: 22,
                      height: 22,
                      borderRadius: "50%",
                      background: "var(--wf-footer-ink)",
                      color: "var(--wf-footer-paper)",
                      fontSize: 11,
                      animationDelay: "0.8s",
                    }}
                  >
                    ↗
                  </span>
                </span>
                <span style={{ display: "block", fontSize: 13, lineHeight: 1.6, color: "var(--wf-footer-mute)" }}>
                  Who signed what
                </span>
              </a>
            </div>
          )}
        </div>

        <div style={{ position: "relative", overflow: "hidden", height: 150, marginTop: 28 }}>
          {WAVES.map((w) => (
            <div
              key={w.height}
              aria-hidden
              style={{
                position: "absolute",
                left: 0,
                right: 0,
                bottom: 0,
                height: w.height,
                overflow: "hidden",
                pointerEvents: "none",
                opacity: w.opacity,
              }}
            >
              <svg
                width="2400"
                height={w.height}
                viewBox={`0 0 2400 ${w.height}`}
                preserveAspectRatio="none"
                xmlns="http://www.w3.org/2000/svg"
                className="wf-wave"
                style={
                  {
                    display: "block",
                    width: 2400,
                    height: w.height,
                    "--wf-wave-dur": w.dur,
                    "--wf-wave-delay": w.delay,
                  } as React.CSSProperties
                }
              >
                <path d={w.d} fill={w.fill} />
              </svg>
            </div>
          ))}
          <span
            className="wf-drift"
            style={mono({
              display: "block",
              maxWidth: 1080,
              margin: "0 auto",
              fontWeight: 700,
              fontSize: "clamp(84px, 19.6vw, 232px)",
              lineHeight: 0.78,
              letterSpacing: "-0.05em",
              color: "var(--wf-footer-ink)",
              whiteSpace: "nowrap",
              padding: "0 22px",
              boxSizing: "border-box",
              position: "relative",
            })}
          >
            windfall
          </span>
        </div>
      </div>

      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 20,
          flexWrap: "wrap",
          maxWidth: 1080,
          margin: "0 auto",
          padding: "16px 22px 22px",
          boxSizing: "border-box",
        }}
      >
        <span style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <span
            aria-hidden
            style={{
              display: "block",
              width: 18,
              height: 18,
              backgroundImage: "url(/windfall/brand/windfall-mark-ink.svg)",
              backgroundSize: "contain",
              backgroundRepeat: "no-repeat",
            }}
          />
          <span style={mono({ fontSize: 11, color: "var(--wf-footer-mute)" })}>
            Windfall &copy;2026 &middot; COMPFEST 18 AIC &middot; Team 6 Eyes
          </span>
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: 14 }}>
          {["Jakarta", "10 carts in queue"].map((s) => (
            <span key={s} style={mono({ fontSize: 11, color: "var(--wf-footer-mute)" })}>
              {s}
            </span>
          ))}
        </span>
      </div>
    </div>
  );
}
