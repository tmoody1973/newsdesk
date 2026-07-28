import fs from "node:fs/promises";
import path from "node:path";

import { parse } from "yaml";

export const dynamic = "force-dynamic";

type Rule = {
  id: string;
  name: string;
  why?: string;
  why_changed?: string;
  layers?: string[];
  check?: string;
};

export default async function Policy() {
  const raw = await fs.readFile(
    path.join(process.cwd(), "..", "policy", "policy.yaml"),
    "utf-8",
  );
  const doc = parse(raw) as { rules?: Rule[]; version?: string | number };
  const rules = doc.rules ?? [];

  return (
    <main>
      <h1 className="font-display text-4xl uppercase tracking-wide">Editorial policy</h1>
      <p className="mt-2 max-w-2xl text-graphite">
        The standards desk, in a file, versioned, with its reasoning attached to each
        rule. Every block prompt is checked against this before generation — so a
        rejected prompt costs $0.
      </p>

      <div className="mt-10 space-y-8">
        {rules.map((rule) => (
          <article key={rule.id} className="border-t-2 border-ink pt-4">
            <div className="flex flex-wrap items-baseline gap-3">
              <span className="mono text-sm text-stamp-red">{rule.id}</span>
              <h2 className="font-display text-2xl uppercase leading-none">{rule.name}</h2>
            </div>

            {rule.why ? <p className="mt-3 max-w-3xl text-sm">{rule.why}</p> : null}

            {rule.check ? (
              <p className="mono mt-3 max-w-3xl border-l-2 border-graphite/40 pl-3 text-xs text-graphite">
                {rule.check}
              </p>
            ) : null}

            {rule.why_changed ? (
              <details className="mt-3 max-w-3xl">
                <summary className="mono cursor-pointer text-xs uppercase tracking-widest text-approval-blue">
                  This rule changed — what it used to say
                </summary>
                <p className="mt-2 text-sm text-graphite">{rule.why_changed}</p>
              </details>
            ) : null}
          </article>
        ))}
      </div>

      <p className="mt-12 max-w-2xl text-sm text-graphite">
        Rules carry their own history. When testing kills an assumption the wrong version
        stays in the record next to the right one, because a standards document that
        quietly edits itself is not one anybody should trust.
      </p>
    </main>
  );
}
