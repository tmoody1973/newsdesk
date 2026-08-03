/** Talking to the Fly worker.
 *
 *  A run is ~5 minutes, so nothing here waits for one. `startRun` posts and
 *  gets a 202 back; everything after that is `pollRun` against the state the
 *  pipeline saves to B2 after every stage. That is the whole architecture —
 *  no queue, no websocket, no database.
 */

import type { RunState } from "./types";

const BASE = process.env.NEXT_PUBLIC_WORKER_URL ?? "http://localhost:8080";

export type Stage = "script" | "gate" | "blocks" | "narration" | "assembly" | "caption";

export class WorkerError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function post(path: string, body: unknown, accessCode: string) {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(accessCode ? { "X-Access-Code": accessCode } : {}),
    },
    body: JSON.stringify(body),
  });
  const payload = await res.json().catch(() => ({}));
  if (!res.ok) {
    // The server's refusals are written for a journalist to act on — it names
    // the unsourced fact rather than saying "422". Surface it verbatim rather
    // than replacing it with something friendlier and emptier.
    throw new WorkerError(payload.error ?? `worker returned ${res.status}`, res.status);
  }
  return payload;
}

export async function startRun(opts: {
  story: unknown;
  stages: Stage[];
  approver?: string;
  accessCode: string;
}): Promise<{ run_id: string; stages: Stage[] }> {
  return post(
    "/runs",
    { story: opts.story, stages: opts.stages, approver: opts.approver ?? "" },
    opts.accessCode,
  );
}

/** A fact the model proposes from a pasted article, with the sentence it came
 *  from. The quote is the whole point: the journalist confirms a proposal by
 *  reading the source line, not by trusting the paraphrase. */
export type FactProposal = { text: string; quote: string; url: string };

/** `POST /ingest` — paste a link, get proposed facts back.
 *
 *  Synchronous, unlike `/runs`: it is one cheap call, so there is nothing to
 *  poll. A 422 here is the server refusing a page it could not read, and its
 *  message names the fallback ("paste the text of the story instead") — which
 *  is why callers show `WorkerError.message` rather than their own wording. */
export async function ingestUrl(
  url: string,
  accessCode: string,
): Promise<{ proposals: FactProposal[]; dropped: number }> {
  return post("/ingest", { url }, accessCode);
}

export async function pollRun(runId: string): Promise<RunState | null> {
  const res = await fetch(`${BASE}/runs/${runId}`, { cache: "no-store" });
  if (!res.ok) return null;
  return res.json();
}

/** Poll until `done` says so, or until the budget runs out.
 *
 *  The budget is not politeness — a run that dies without writing an `error`
 *  event would otherwise spin this forever and the page would look busy while
 *  nothing happened. Callers get `null` and can say so.
 */
export async function waitFor(
  runId: string,
  done: (state: RunState) => boolean,
  opts: { everyMs?: number; forMs?: number; onTick?: (s: RunState) => void } = {},
): Promise<RunState | null> {
  const every = opts.everyMs ?? 2500;
  const until = Date.now() + (opts.forMs ?? 10 * 60_000);

  // A run that failed before can be re-posted, and its state keeps the old
  // failure in the log — corrections stay in the record. So "an error exists"
  // is not "this run has failed": only an error NEWER than the events we saw
  // on the first poll ends the wait. Judging any-error-ever made a retry
  // return the previous run's corpse instantly while the new run was still
  // working.
  let baseline: string | null = null;

  while (Date.now() < until) {
    const state = await pollRun(runId);
    if (state) {
      opts.onTick?.(state);
      const newest = state.events[state.events.length - 1];
      if (baseline === null) baseline = newest?.ts ?? "";
      if (newest?.kind === "error" && newest.ts > baseline) return state;
      if (done(state)) return state;
    }
    await new Promise((r) => setTimeout(r, every));
  }
  return null;
}

export function lastError(state: RunState | null): string | null {
  if (!state) return null;
  // Only a run that ENDED in error has failed. Older errors in the log are
  // refusals the run recovered from — the record, not the verdict. Reporting
  // them as the outcome showed a failure banner over a successful script.
  const newest = state.events[state.events.length - 1];
  return newest?.kind === "error" ? newest.message : null;
}
