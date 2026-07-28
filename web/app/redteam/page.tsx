import fs from "node:fs/promises";
import path from "node:path";

import { Stamp } from "@/components/Stamp";

export const dynamic = "force-dynamic";

type Probe = {
  id: string;
  title: string;
  input: string;
  expected: "refuse" | "pass";
  passed: boolean;
  findings: { rule_id: string; message: string }[];
  explain?: string;
};

export default async function RedTeam() {
  const raw = await fs.readFile(
    path.join(process.cwd(), "public", "redteam.json"),
    "utf-8",
  );
  const data = JSON.parse(raw) as {
    generated_at: string;
    spend_usd: number;
    probes: Probe[];
  };

  return (
    <main>
      <h1 className="font-display text-4xl uppercase tracking-wide">Red team</h1>
      <p className="mt-2 max-w-2xl text-graphite">
        Production readiness is proven by what a system refuses. Five adversarial
        requests, every rejection citing a rule by number, and a spend counter that
        reads exactly zero.
      </p>

      <div className="mono mt-6 flex flex-wrap items-center gap-x-8 gap-y-2 border-y-2 border-ink py-3 text-xs">
        <span className="text-approval-blue">
          ${data.spend_usd.toFixed(2)} spent on {data.probes.length} probes
        </span>
        <span className="text-graphite">
          produced {data.generated_at.slice(0, 19).replace("T", " ")} UTC
        </span>
      </div>

      <p className="mt-6 max-w-2xl text-sm text-graphite">
        The zero is not a rounding. <span className="mono">gate.py</span> has no provider
        access at all, and a test walks its import graph and fails the build if anything
        network-capable ever appears in it. These are the same probe texts the test suite
        asserts against — if this page showed different inputs, it would be a claim about
        the gate rather than a view of it.
      </p>

      <div className="mt-8 space-y-4">
        {data.probes.map((probe) => {
          const wantRefused = probe.expected === "refuse";
          const correct = probe.passed !== wantRefused;
          return (
            <article
              key={probe.id}
              className="border-2 border-ink p-5"
              style={{ borderColor: correct ? undefined : "var(--color-stamp-red)" }}
            >
              <header className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <span className="mono text-xs uppercase tracking-widest text-graphite">
                    {probe.id}
                  </span>
                  <h2 className="font-display text-xl uppercase leading-tight">
                    {probe.title}
                  </h2>
                </div>
                {probe.passed ? (
                  <Stamp kind="approved" label="Passed" rotate={2} />
                ) : (
                  <Stamp kind="blocked" label="Blocked" />
                )}
              </header>

              <p className="mono mt-4 border-l-2 border-graphite/40 pl-3 text-xs text-graphite">
                {probe.input}
              </p>

              {probe.findings.length > 0 ? (
                <ul className="mono mt-4 space-y-2 text-xs">
                  {probe.findings.map((f, i) => (
                    <li key={i} className="text-stamp-red">
                      <span className="font-medium">{f.rule_id}</span> — {f.message}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-4 text-sm text-approval-blue">
                  {probe.id === "R5"
                    ? "Passes — and that is the point. The gate teaches the boundary instead of dead-ending: the same request, reframed as an abstract silhouette with no likeness, is allowed through."
                    : "No rule fired."}
                </p>
              )}
            </article>
          );
        })}
      </div>
    </main>
  );
}
