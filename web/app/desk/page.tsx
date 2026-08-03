import Link from "next/link";

import { listRuns } from "@/lib/b2";
import type { RunState } from "@/lib/types";

export const dynamic = "force-dynamic";

/** The mockup's five status tags. Blocked is solid accent; published is solid
 *  blue; everything mid-flight is quiet. Colour is never the only signal — the
 *  label says the state too. */
const TAG: Record<string, { style: React.CSSProperties; label: string }> = {
  drafting: { style: { background: "var(--color-neutral-100)", color: "var(--color-neutral-800)" }, label: "Drafting" },
  generating: { style: { background: "var(--color-neutral-100)", color: "var(--color-neutral-800)" }, label: "Generating" },
  awaiting_approval: { style: { background: "#dde6f2", color: "#1d3f73" }, label: "Awaiting approval" },
  published: { style: { background: "#2b5da8", color: "#fff" }, label: "Published" },
  blocked: { style: { background: "var(--color-accent)", color: "#fff" }, label: "Blocked" },
};

function Blocks({ run }: { run: RunState }) {
  const total = run.blocks.length || 6;
  const ready = run.blocks.filter((b) => b.status === "ready").length;
  const pct = Math.round((ready / total) * 100);
  const fill =
    run.status === "blocked" ? "var(--color-accent)"
    : run.status === "published" || run.status === "awaiting_approval" ? "#2b5da8"
    : "var(--color-neutral-700)";
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
      <span className="mono" style={{ fontSize: 12 }}>{ready}/{total}</span>
      <span style={{ display: "inline-block", width: 60, height: 6, background: "var(--color-neutral-300)" }}>
        <span style={{ display: "block", width: `${pct}%`, height: "100%", background: fill }} />
      </span>
    </span>
  );
}

export default async function Desk() {
  // A run with no words in it is not a story — it is scaffolding that touched
  // the bucket. Filtered on narration, not on block count: block count is 6 from
  // the moment a run is created and would make this a no-op that looked careful.
  const runs = (await listRuns()).filter((run) =>
    run.blocks.some((block) => block.narration.trim().length > 0),
  );
  const awaiting = runs.filter((r) => r.status === "awaiting_approval").length;

  return (
    <main>
      <div
        style={{
          display: "flex", alignItems: "baseline", gap: 16,
          borderBottom: "2px solid var(--color-divider)", paddingBottom: 14,
        }}
      >
        <h1 className="anton" style={{ fontSize: 32, letterSpacing: ".01em", margin: 0 }}>
          THE DESK
        </h1>
        <span className="mono" style={{ fontSize: 11, color: "var(--color-neutral-600)" }}>
          {runs.length} {runs.length === 1 ? "story" : "stories"} · {awaiting} awaiting approval
        </span>
        <Link
          href="/about"
          className="mono"
          style={{ fontSize: 11, color: "var(--color-accent)", textDecoration: "none" }}
        >
          new here? how Newsdesk works →
        </Link>
        <span style={{ flex: 1 }} />
        <Link href="/new" className="btn btn-primary" style={{ fontSize: 16, padding: "12px 22px" }}>
          Start a story
        </Link>
      </div>

      {runs.length > 0 ? (
        <table className="table" style={{ marginTop: 4 }}>
          <thead>
            <tr>
              <th>Story</th>
              <th>Status</th>
              <th>Blocks</th>
              <th>Approver</th>
              <th>Updated</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => {
              const tag = TAG[run.status] ?? TAG.drafting;
              return (
                <tr key={run.run_id}>
                  <td style={{ fontWeight: 600 }}>
                    <Link href={`/runs/${run.run_id}`} style={{ color: "inherit", textDecoration: "none" }}>
                      {run.story}
                    </Link>
                  </td>
                  <td>
                    <span className="tag" style={tag.style}>{tag.label}</span>
                  </td>
                  <td><Blocks run={run} /></td>
                  <td>{run.approval ? run.approval.approver : "—"}</td>
                  <td className="mono" style={{ fontSize: 12, color: "var(--color-neutral-600)" }}>
                    {(run.created_at ?? "").slice(0, 10)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      ) : null}

      <div
        style={{
          marginTop: 40, border: "1px dashed var(--color-divider)",
          padding: 28, maxWidth: 520,
        }}
      >
        <p style={{ fontWeight: 600, margin: "0 0 4px" }}>Nothing on the board?</p>
        <p style={{ fontSize: 13, color: "var(--color-neutral-700)", margin: "0 0 12px" }}>
          Start with facts — the video comes later.
        </p>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <Link href="/new" className="btn btn-primary">Start a story</Link>
          <Link href="/new?case=cs2" className="btn btn-ghost">Load a case study</Link>
        </div>
      </div>
    </main>
  );
}
