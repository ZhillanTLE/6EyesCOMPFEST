/**
 * Recovery API client.
 *
 * Same-origin by design: next.config.ts rewrites /api/recovery/* to Flask, so
 * nothing here needs a backend hostname and no API origin ends up in the
 * client bundle.
 */
import type { QueueResponse, RecoveryResult } from "./types";

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { error?: string };
      if (body?.error) detail = body.error;
    } catch {
      /* response had no JSON body; the status text is all we have */
    }
    throw new Error(detail);
  }
  return (await res.json()) as T;
}

export async function fetchQueue(signal?: AbortSignal): Promise<QueueResponse> {
  return json<QueueResponse>(await fetch("/api/recovery/queue", { signal }));
}

export async function runRecovery(
  travelerId: string,
  signal?: AbortSignal,
): Promise<RecoveryResult> {
  return json<RecoveryResult>(
    await fetch("/api/recovery/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ traveler_id: travelerId }),
      signal,
    }),
  );
}
