/**
 * Recovery API client.
 *
 * Same-origin by design: next.config.ts rewrites /api/recovery/* to Flask, so
 * nothing here needs a backend hostname and no API origin ends up in the
 * client bundle.
 */
import type { QueueResponse, RecoveryResult, SendReceipt } from "./types";

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

/**
 * Wrapper aman untuk menangani network/connection error vs API error.
 */
async function safeFetch<T>(input: RequestInfo | URL, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(input, init);
  } catch (error: any) {
    // Terjadi jika jaringan benar-benar terputus total
    throw new Error("Koneksi ke backend terputus. Pastikan server Flask atau Docker sudah menyala.");
  }

  // Jika Next.js mengembalikan error karena proxy gagal menyambung ke backend (biasanya status 500/502/504 dari proxy)
  if (!res.ok) {
    if (res.status === 500 || res.status === 502 || res.status === 504) {
      throw new Error("Koneksi ke backend terputus. Pastikan server Flask atau Docker sudah menyala.");
    }
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { error?: string };
      if (body?.error) detail = body.error;
    } catch {
      /* no json body */
    }
    throw new Error(detail);
  }

  return (await res.json()) as T;
}

export async function fetchQueue(signal?: AbortSignal): Promise<QueueResponse> {
  return safeFetch<QueueResponse>("/api/recovery/queue", { signal });
}

export async function runRecovery(
  travelerId: string,
  signal?: AbortSignal,
): Promise<RecoveryResult> {
  return safeFetch<RecoveryResult>(
    "/api/recovery/run",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ travelerId }),
      signal,
    },
  );
}

/**
 * Deliver the approved notification.
 *
 * Deliberately a separate call from runRecovery. Reading a trace must never
 * send anything; delivery needs its own explicit click.
 */
export async function approveAndSend(
  travelerId: string,
  signal?: AbortSignal,
): Promise<SendReceipt> {
  return safeFetch<SendReceipt>(
    "/api/recovery/send",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ travelerId }),
      signal,
    },
  );
}