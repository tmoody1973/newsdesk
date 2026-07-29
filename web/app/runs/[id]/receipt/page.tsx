import Link from "next/link";
import { notFound } from "next/navigation";

import { Stamp } from "@/components/Stamp";
import { finalVideo, getRun } from "@/lib/b2";

export const dynamic = "force-dynamic";

/**
 * The public nutrition label, designed as a chit: narrow column, perforated top
 * edge, mono-dominant. Machine truth always renders in mono.
 *
 * Refusals are disclosed rather than hidden — a receipt that only lists what was
 * made, and stays silent about what was refused, is marketing.
 */
export default async function Receipt({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const run = await getRun(id);
  if (!run) notFound();

  const video = await finalVideo(id);
  const blocks = [...run.blocks].sort((a, b) => a.n - b.n);
  const runtime = blocks.reduce((sum, b) => sum + (b.voice_duration_s ?? 0), 0);
  const refusals = run.events.filter((e) => e.rule_id).length;
  // Read from the event log, not from `block.attempts`.
  //
  // `stage_narration` replaces a block's `attempts` tuple rather than appending
  // to it, and `stage_blocks` never wrote one — so `attempts` names the voice
  // and nothing else, and this section listed `elevenlabs · eleven_v3` for a
  // run whose six clips were made by seedance. The event log is the audit trail
  // and it carries the model that actually ran on every stage, which is the
  // claim the copy below already makes. Attempts are still folded in: they are
  // where a fallback's rejected first try is recorded.
  const models = new Set(
    [
      ...run.events.map((e) => ({ provider: e.provider, model: e.model })),
      ...run.blocks.flatMap((b) => b.attempts),
    ]
      .filter((m) => m.model)
      .map((m) => (m.provider ? `${m.provider} · ${m.model}` : m.model!)),
  );

  return (
    <main className="mx-auto max-w-2xl">
      <Link href={`/runs/${id}`} className="mono text-xs text-approval-blue underline">
        ← Run board
      </Link>

      <article className="mt-4 border-2 border-ink bg-pasteboard">
        {/* Perforated top edge — this is a chit, not a page. */}
        <div
          className="h-3 border-b-2 border-dashed border-ink"
          style={{
            backgroundImage:
              "radial-gradient(circle at 6px 12px, transparent 4px, var(--color-ink) 4px, transparent 5px)",
            backgroundSize: "12px 12px",
          }}
        />

        <div className="p-6 sm:p-8">
          <h1 className="font-display text-3xl uppercase leading-none">Receipt</h1>

          <Section title="What you're watching">
            <Row label="Story" value={run.story} />
            <Row label="Runtime" value={`${runtime.toFixed(1)}s of narration across ${blocks.length} blocks`} />
            <Row label="Run" value={run.run_id} mono />
            <Row label="Created" value={(run.created_at ?? "").slice(0, 19).replace("T", " ")} mono />
          </Section>

          <Section title="Facts it is allowed to assert">
            <ul className="space-y-3">
              {run.facts.map((fact) => (
                <li key={fact.id} className="text-sm">
                  <span className="mono text-approval-blue">{fact.id}</span> {fact.text}
                  <div className="mono mt-1 text-[11px] text-graphite">
                    {fact.sources.map((s) => s.value).join(" · ") || "— no source recorded"}
                  </div>
                </li>
              ))}
              {run.facts.length === 0 ? (
                <li className="text-sm text-graphite">No facts recorded on this run.</li>
              ) : null}
            </ul>
          </Section>

          <Section title="Every claim, and where it came from">
            <div className="space-y-4">
              {blocks.map((block) => (
                <div key={block.n} className="border-l-2 border-graphite/40 pl-3">
                  <div className="mono text-xs uppercase text-graphite">Block {block.n}</div>
                  <p className="mt-1 text-sm">{block.narration}</p>
                  {block.claims.length ? (
                    <ul className="mono mt-2 space-y-1 text-[11px]">
                      {block.claims.map((claim, i) => (
                        <li key={i}>
                          <span className="text-approval-blue">{claim.fact_id}</span>
                          {" ← "}
                          <span>&ldquo;{claim.spoken}&rdquo;</span>
                          {" ⇢ "}
                          <span className="text-graphite">{claim.evidence}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <div className="mono mt-2 text-[11px] text-graphite">
                      No quantities asserted in this line.
                    </div>
                  )}
                </div>
              ))}
            </div>
          </Section>

          <Section title="Made by">
            <ul className="mono space-y-1 text-xs">
              {[...models].map((m) => (
                <li key={m}>{m}</li>
              ))}
            </ul>
            <p className="mt-3 text-xs text-graphite">
              The manifest records the model that <em>ran</em>, not the one that was asked
              first. A substitution nobody can see in the record is not a fallback.
            </p>
          </Section>

          <Section title="Checked against policy">
            <p className="text-sm">
              Six rules, POL-1 to POL-6, applied to every block before generation.{" "}
              {refusals === 0
                ? "No prompt was refused on this run."
                : `${refusals} prompt(s) refused during production.`}{" "}
              A refused prompt costs $0 — the gate has no provider access at all.
            </p>
            <Link href="/policy" className="mono mt-2 inline-block text-xs text-approval-blue underline">
              Read the rules →
            </Link>
          </Section>

          <Section title="Approved by">
            {run.approval ? (
              <div className="flex flex-wrap items-center gap-4">
                <Stamp kind="approved" label="Approved" />
                <div className="text-sm">
                  <div>{run.approval.approver}</div>
                  <div className="mono text-xs text-graphite">
                    {run.approval.ts.slice(0, 19).replace("T", " ")} UTC
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-sm text-stamp-red">
                Not approved. This run has not been through the editorial gate.
              </p>
            )}
          </Section>

          <Section title="Verify it yourself">
            <p className="text-sm">
              Do not take our word for it. The manifest is embedded in the MP4 itself, and
              the assets it names are public — so this check does not need our permission
              and does not trust our website.
            </p>
            {/* The filename comes from this run's own video. It was hardcoded to
                `cs1.mp4` — so every receipt but CS-1's told the reader to verify
                a file they had not downloaded, and the one instruction on the
                page whose whole point is "do not trust our website" was the one
                thing on it that was wrong. */}
            <pre className="mono mt-3 overflow-x-auto border-2 border-ink bg-ink/5 p-3 text-[11px]">
{`curl -O ${video ?? "<video url>"}
genblaze verify --fetch ${video?.split("/").pop() || "<file>.mp4"}`}
            </pre>
            <p className="mono mt-2 text-[11px] text-graphite">
              A file that does not match its manifest fails with exit 1. One flipped byte is
              enough.
            </p>
          </Section>
        </div>
      </article>
    </main>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-8 border-t border-graphite/30 pt-5">
      <h2 className="mono mb-3 text-xs uppercase tracking-widest text-graphite">{title}</h2>
      {children}
    </section>
  );
}

function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex flex-wrap justify-between gap-x-6 border-b border-graphite/20 py-1.5 text-sm last:border-0">
      <span className="text-graphite">{label}</span>
      <span className={mono ? "mono text-xs" : ""}>{value}</span>
    </div>
  );
}
