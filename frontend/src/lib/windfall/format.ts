/**
 * Indonesian number formatting, mirroring backend/recovery/formatting.py.
 *
 * Thousands separated by dots, decimals by comma. Applied at the formatter and
 * never stored pre-formatted -- the prototype held "-11.2%" in its seed while
 * its runtime formatter produced commas, so one screen showed both.
 */

export function idr(amount: number | null | undefined): string {
  if (amount === null || amount === undefined) return "—";
  return "IDR " + Math.round(amount).toLocaleString("id-ID");
}

/** A saving is shown as a price drop: 0.1123 -> "−11,2%". */
export function pct(fraction: number | null | undefined): string {
  if (fraction === null || fraction === undefined) return "—";
  const value = fraction * 100;
  const body = Math.abs(value).toFixed(1).replace(".", ",");
  return (value > 0 ? "\u2212" : "+") + body + "%";
}

/** Unsigned, for thresholds: 0.15 -> "15,0%". */
export function plainPct(fraction: number | null | undefined): string {
  if (fraction === null || fraction === undefined) return "—";
  return (fraction * 100).toFixed(1).replace(".", ",") + "%";
}

export function seconds(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return "—";
  return (ms / 1000).toFixed(2).replace(".", ",") + "s";
}

const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "Mei", "Jun",
  "Jul", "Agu", "Sep", "Okt", "Nov", "Des",
];

export function shortDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
}

export function dateRange(from: string, to: string | null): string {
  return to ? `${shortDate(from)} – ${shortDate(to)}` : shortDate(from);
}

export function abandonedLabel(hours: number): string {
  if (hours < 24) return `${hours} jam lalu`;
  if (hours < 48) return "kemarin";
  return `${Math.round(hours / 24)} hari lalu`;
}

export function stars(n: number): string {
  return "\u2605".repeat(Math.max(0, Math.min(5, n)));
}
