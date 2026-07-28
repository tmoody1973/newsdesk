import Link from "next/link";

import { listRuns } from "@/lib/b2";

export const dynamic = "force-dynamic";

const STATUS: Record<string, string> = {
  drafting: "text-graphite",
  generating: "text-canary",
  awaiting_approval: "text-approval-blue",
  published: "text-approval-blue",
  blocked: "text-stamp-red",
};

export default async function Desk() {
  // A run with no words in it is not a story — it is scaffolding that touched
  // the bucket, and the smoke test from MOO-422 leaves exactly that: six
  // placeholder blocks, no facts, no narration. Filtered on narration rather
  // than on block count, because the block count is 6 from the moment a run is
  // created and would have made this check a no-op that only looked careful.
  const runs = (await listRuns()).filter((run) =>
    run.blocks.some((block) => block.narration.trim().length > 0),
  );

  return (
    <main>
      <h1 className="font-display text-4xl uppercase tracking-wide">The Desk</h1>
      <p className="mt-2 max-w-2xl text-graphite">
        Every story on the board. One <span className="mono">state.json</span> per run in
        Backblaze B2 — there is no database, and this page is a renderer over that file
        rather than a second source of truth.
      </p>

      {runs.length === 0 ? (
        <div className="mt-10 border-2 border-dashed border-graphite/50 p-10 text-center">
          <p className="font-display text-xl uppercase">Nothing on the board.</p>
          <p className="mt-2 text-graphite">Start with facts — the video comes later.</p>
        </div>
      ) : (
        <div className="mt-8 overflow-x-auto border-2 border-ink bg-pasteboard">
          <table className="w-full min-w-[42rem] text-left text-sm">
            <thead className="border-b-2 border-ink">
              <tr className="mono text-xs uppercase tracking-wider text-graphite">
                <th className="px-4 py-3">Story</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Blocks</th>
                <th className="px-4 py-3">Approver</th>
                <th className="px-4 py-3">Created</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => {
                const ready = run.blocks.filter((b) => b.status === "ready").length;
                return (
                  <tr key={run.run_id} className="border-b border-graphite/25 last:border-0">
                    <td className="px-4 py-4">
                      <Link
                        href={`/runs/${run.run_id}`}
                        className="font-medium text-approval-blue underline-offset-2 hover:underline"
                      >
                        {run.story}
                      </Link>
                      <div className="mono mt-1 text-xs text-graphite">{run.run_id}</div>
                    </td>
                    <td className={`mono px-4 py-4 text-xs uppercase ${STATUS[run.status] ?? ""}`}>
                      {run.status.replace(/_/g, " ")}
                      {run.final?.uri ? (
                        <div className="mt-1 normal-case text-graphite">
                          {typeof run.final.runtime_s === "number"
                            ? `${(run.final.runtime_s as number).toFixed(1)}s`
                            : null}
                        </div>
                      ) : null}
                    </td>
                    <td className="mono px-4 py-4 text-xs">
                      {ready}/{run.blocks.length || 6}
                    </td>
                    <td className="px-4 py-4 text-xs">
                      {run.approval ? (
                        run.approval.approver
                      ) : (
                        <span className="text-graphite">— not approved</span>
                      )}
                    </td>
                    <td className="mono px-4 py-4 text-xs text-graphite">
                      {(run.created_at ?? "").slice(0, 16).replace("T", " ")}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <section className="mt-12 grid gap-4 md:grid-cols-3">
        {[
          {
            title: "Facts",
            body: "A story is a set of facts, each carrying a source. A fact without one cannot be submitted — enforced by a pure function with no provider access.",
          },
          {
            title: "Policy",
            body: "Every block prompt is checked before generation. A rejected prompt costs $0, and a test walks the gate's import graph to prove it cannot reach a provider.",
          },
          {
            title: "Approval",
            body: "Assembly is unreachable without a named human. Their name and timestamp become part of the video's permanent record.",
          },
        ].map((wall, i) => (
          <div key={wall.title} className="border-2 border-ink p-5">
            <div className="mono text-xs uppercase tracking-widest text-graphite">
              Wall {i + 1}
            </div>
            <h2 className="mt-1 font-display text-xl uppercase">{wall.title}</h2>
            <p className="mt-2 text-sm text-graphite">{wall.body}</p>
          </div>
        ))}
      </section>
    </main>
  );
}
