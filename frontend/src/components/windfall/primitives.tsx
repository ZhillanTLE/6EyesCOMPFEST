/**
 * Leaf primitives, ported from the design-system bundle.
 *
 * Every colour is a var(--wf-*) reference; the tokens file is the only place a
 * hex literal lives. Semantic colour stays rationed to exactly two jobs --
 * ledger rows that pass or fail, and amber markers on previews and genuine
 * price deadlines. Nowhere else.
 */
import type { CSSProperties, ReactNode } from "react";

/* ── Button ───────────────────────────────────────────────────────────────
   Ink fill, hairline outline, or ghost. */
export function Button({
  variant = "primary",
  size = "md",
  full = true,
  disabled = false,
  children,
  onClick,
  style,
  ...rest
}: {
  variant?: "primary" | "outline" | "ghost";
  size?: "sm" | "md";
  full?: boolean;
  disabled?: boolean;
  children: ReactNode;
  onClick?: () => void;
  style?: CSSProperties;
} & Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, "style" | "onClick">) {
  const variants: Record<string, CSSProperties> = {
    primary: { background: "var(--wf-ink)", color: "var(--wf-paper)" },
    outline: {
      background: "transparent",
      color: "var(--wf-ink)",
      boxShadow: "var(--wf-ring-ink)",
    },
    ghost: { background: "transparent", color: "var(--wf-ink-2)" },
  };
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 8,
        width: full ? "100%" : "auto",
        padding: size === "sm" ? "9px 16px" : "13px 20px",
        boxSizing: "border-box",
        fontSize: 13,
        fontWeight: 500,
        lineHeight: 1.6,
        letterSpacing: "0.01em",
        borderRadius: "var(--wf-radius-md)",
        border: "none",
        cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? 0.45 : 1,
        transition: "opacity .12s ease",
        ...variants[variant],
        ...style,
      }}
      {...rest}
    >
      {children}
    </button>
  );
}

/* ── ModelTag ─────────────────────────────────────────────────────────────
   Model provenance as a text chip, never a logo. */
export function ModelTag({ children }: { children: ReactNode }) {
  return (
    <span
      className="wf-eyebrow"
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "4px 7px",
        fontSize: 9,
        borderRadius: "var(--wf-radius-sm)",
        boxShadow: "var(--wf-ring-rule)",
        whiteSpace: "nowrap",
      }}
    >
      {children}
    </span>
  );
}

/* ── PreviewTag ───────────────────────────────────────────────────────────
   Amber marker: this notification is a draft and has not been sent. */
export function PreviewTag({ children = "preview only" }: { children?: ReactNode }) {
  return (
    <span
      className="wf-eyebrow"
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "5px 9px",
        fontSize: 9,
        fontWeight: 700,
        borderRadius: "var(--wf-radius-sm)",
        background: "var(--wf-amber-tint)",
        boxShadow: "inset 0 0 0 1px var(--wf-amber-border)",
        color: "var(--wf-amber)",
        whiteSpace: "nowrap",
      }}
    >
      {children}
    </span>
  );
}

/* ── StatusPill ───────────────────────────────────────────────────────────
   Ledger outcome text. The only green and the only red in the console. */
export function StatusPill({
  tone = "neutral",
  children,
}: {
  tone?: "pass" | "fail" | "neutral";
  children: ReactNode;
}) {
  const tones = {
    pass: "var(--wf-signal-ink)",
    fail: "var(--wf-halt)",
    neutral: "var(--wf-ink-3)",
  };
  return (
    <span
      className="wf-mono"
      style={{ fontSize: 12, lineHeight: 1.6, color: tones[tone], whiteSpace: "nowrap" }}
    >
      {children}
    </span>
  );
}

/* ── TierBadge ────────────────────────────────────────────────────────────
   The Classifier's conclusion, boxed in an ink ring.

   `source` matters: a cold-start tier is derived from the cart, not from
   history, and saying so is the difference between a proxy and a claim. */
export function TierBadge({
  tier,
  threshold,
  source = "history",
}: {
  tier: string;
  threshold: string;
  source?: string;
}) {
  const proxy = source === "cart_proxy";
  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 12,
        minHeight: 40,
        padding: "0 14px",
        borderRadius: "var(--wf-radius-md)",
        boxShadow: "var(--wf-ring-ink)",
        boxSizing: "border-box",
      }}
    >
      <span className="wf-eyebrow" style={{ fontSize: 9 }}>
        Tingkatan
      </span>
      <span style={{ fontSize: 15, fontWeight: 500, color: "var(--wf-ink)" }}>{tier}</span>
      {proxy && (
        <span className="wf-eyebrow" style={{ fontSize: 9, color: "var(--wf-amber)" }}>
          dari cart
        </span>
      )}
      <span
        className="wf-eyebrow"
        style={{ fontSize: 9, paddingLeft: 10, borderLeft: "var(--wf-border-hair)" }}
      >
        {threshold}
      </span>
    </div>
  );
}

/* ── Skeleton ─────────────────────────────────────────────────────────────
   Placeholder bar for a stage that is genuinely still running. */
export function Skeleton({ width = "100%", height = 8 }: { width?: string | number; height?: number }) {
  return (
    <span
      className="wf-skeleton"
      style={{
        display: "block",
        width,
        height,
        borderRadius: "var(--wf-radius-sm)",
        background: "var(--wf-surface)",
        boxShadow: "var(--wf-ring-rule)",
      }}
    />
  );
}
