import Link from "next/link";
import { notFound } from "next/navigation";

import { Stamp } from "@/components/Stamp";
import { finalVideo, getRun } from "@/lib/b2";

export const dynamic = "force-dynamic";

const ROLES = ["cold open", "stakes", "evidence", "evidence", "turn", "kicker"];

/** The take against the published window. Blue when it landed, graphite when it
 *  is a runtime cost rather than a fault — since design spec §6.6 made block
 *  length follow the take, an out-of-window take no longer desyncs anything. */
function takeBadge(seconds: number | null) {
  if (seconds == null) return <span className="mono text-xs text-graphite">no take</span>;
  const inWindow = seconds >= 9.0 && seconds <= 13.0;
  return (
    <span className={`mono text-xs ${inWindow ? "text-approval-blue" : "text-graphite"}`}>
      {seconds.toFixed(2)}s {inWindow ? "✓" : "· outside window"}
    </span>
  );
}

export default async function RunBoard({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const run = await getRun(id);
  if (!run) notFound();

  const video = await finalVideo(id);
  const blocks = [...run.blocks].sort((a, b) => a.n - b.n);
  const spend = run.events.reduce((sum, e) => sum + (e.cost_usd ?? 0), 0);
  const runtime = blocks.reduce((sum, b) => sum + (b.voice_duration_s ?? 0), 0);

  return (
    <main>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl uppercase tracking-wide">{run.story}</h1>
          <p className="mono mt-1 text-xs text-graphite">{run.run_id}</p>
        </div>
        {run.approval ? (
          <Stamp kind="approved" label="Approved" suffix={run.approval.approver} />
        ) : (
          <Stamp kind="retry" label="Awaiting approval" rotate={2} />
        )}
      </div>

      <div className="mono mt-6 flex flex-wrap gap-x-8 gap-y-2 border-y-2 border-ink py-3 text-xs">
        <span>{blocks.length} blocks</span>
        <span>{runtime.toFixed(1)}s narration</span>
        <span>${spend.toFixed(4)} spent</span>
        <span>{run.facts.length} facts</span>
        {run.approval ? <span>approved {run.approval.ts.slice(0, 19).replace("T", " ")}</span> : null}
        <Link href={`/runs/${id}/receipt`} className="text-approval-blue underline">
          Receipt →
        </Link>
      </div>

      {video ? (
        <section className="mt-8">
          <h2 className="font-display text-xl uppercase">The film</h2>
          <video
            controls
            preload="metadata"
            src={video}
            className="mt-3 w-full max-w-[360px] border-2 border-ink bg-ink"
          />
        </section>
      ) : null}

      <section className="mt-10">
        <h2 className="font-display text-xl uppercase">The board</h2>
        <p className="mt-1 text-sm text-graphite">
          Six blocks, one per beat. Each card shows the provider that actually ran — a
          fallback nobody can see in the record is a substitution, not a fallback.
        </p>
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {blocks.map((block) => {
            const last = block.attempts[block.attempts.length - 1];
            const fellBack = block.attempts.some((a) => a.provider === "lmnt");
            return (
              <article key={block.n} className="border-2 border-ink p-4">
                <header className="flex items-baseline justify-between">
                  <span className="font-display text-lg uppercase">Block {block.n}</span>
                  <span className="mono text-xs text-graphite">
                    {ROLES[block.n - 1] ?? ""}
                  </span>
                </header>

                <p className="mt-3 text-sm leading-snug">{block.narration}</p>

                <div className="mt-3 flex flex-wrap items-center gap-2">
                  {block.fact_ids.map((f) => (
                    <span
                      key={f}
                      className="mono rounded-full border border-approval-blue px-2 py-0.5 text-[11px] text-approval-blue"
                    >
                      {f}
                    </span>
                  ))}
                  {block.fact_ids.length === 0 ? (
                    <span className="mono text-[11px] text-graphite">no claims mapped</span>
                  ) : null}
                </div>

                <div className="mt-4 border-t border-graphite/30 pt-3">
                  {takeBadge(block.voice_duration_s)}
                  <div className="mono mt-1 text-[11px] text-graphite">
                    {last ? `${last.provider} · ${last.model}` : "—"}
                  </div>
                  {fellBack ? (
                    <div className="mt-3">
                      <Stamp kind="retry" label="Fallback" suffix="lmnt" rotate={-2} />
                    </div>
                  ) : null}
                </div>
              </article>
            );
          })}
        </div>
      </section>

      <section className="mt-12">
        <h2 className="font-display text-xl uppercase">Run log</h2>
        <p className="mt-1 text-sm text-graphite">
          Every submission, rejection, retry and take measurement, newest first. This is
          literally the audit trail rendered.
        </p>
        <ol className="mono mt-4 space-y-1 border-2 border-ink p-4 text-xs">
          {[...run.events].reverse().map((e, i) => (
            <li key={i} className="flex flex-wrap gap-x-3">
              <span className="text-graphite">{e.ts.slice(11, 19)}</span>
              <span className="uppercase text-approval-blue">{e.kind}</span>
              <span>{e.message}</span>
              {e.cost_usd ? <span className="text-graphite">${e.cost_usd.toFixed(4)}</span> : null}
            </li>
          ))}
          {run.events.length === 0 ? <li className="text-graphite">No events recorded.</li> : null}
        </ol>
      </section>
    </main>
  );
}
