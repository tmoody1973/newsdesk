"use client";

/**
 * Editor Review — mockup 1j. Wall 3, and the only screen in this product that
 * collects a human's name.
 *
 * The order is deliberate and it is the design's: a block is approved by
 * looking at it, and the stamp at the bottom right is unreachable until every
 * block has been. That is the whole argument — approval is not a button at the
 * end of a form, it is the last thing left after somebody has watched six
 * clips.
 *
 * The note under the stamp is not decoration either. "Your name and this
 * timestamp become part of the video's permanent record" is literally true:
 * `state.approve()` writes it, `build_run` puts it in the manifest, and
 * `genblaze verify` reads it back out of the MP4. It should be read before the
 * click, not discovered after.
 */

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Stamp } from "@/components/Stamp";
import type { RunState } from "@/lib/types";
import { WorkerError, startRun } from "@/lib/worker";

export function EditorReview({ run }: { run: RunState }) {
  const router = useRouter();
  const blocks = [...run.blocks].sort((a, b) => a.n - b.n);

  const [approved, setApproved] = useState<Set<number>>(new Set());
  const [approver, setApprover] = useState("");
  const [accessCode, setAccessCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  const alreadyPublished = run.status === "published";
  const allSeen = blocks.length > 0 && blocks.every((b) => approved.has(b.n));
  const canStamp = allSeen && approver.trim().length > 1 && !busy;

  function toggle(n: number) {
    setApproved((prev) => {
      const next = new Set(prev);
      if (next.has(n)) next.delete(n);
      else next.add(n);
      return next;
    });
  }

  async function stamp() {
    setProblem(null);
    setBusy(true);
    try {
      await startRun({
        // The story is re-posted because the worker parses it on every call —
        // one parser, one standard, no "trusted" path that skips Wall 1.
        story: storyFromRun(run),
        stages: ["assembly"],
        approver: approver.trim(),
        accessCode,
      });
      router.push(`/runs/${run.run_id}/receipt`);
    } catch (err) {
      setProblem(err instanceof WorkerError ? err.message : String(err));
      setBusy(false);
    }
  }

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 380px", gap: 32 }}>
      <div>
        <div
          style={{
            display: "flex",
            alignItems: "baseline",
            gap: 16,
            borderBottom: "2px solid var(--color-divider)",
            paddingBottom: 14,
            marginBottom: 20,
          }}
        >
          <h1 className="anton" style={{ fontWeight: 400, fontSize: 28, margin: 0 }}>
            EDITOR REVIEW
          </h1>
          <span className="mono" style={{ fontSize: 11, color: "var(--color-neutral-600)" }}>
            {run.story}
          </span>
        </div>

        <p style={{ fontSize: 13, lineHeight: 1.6, color: "var(--color-neutral-700)", margin: "0 0 16px", maxWidth: 640 }}>
          This is the sign-off. Watch each block — picture and narration together —
          and approve what you&apos;d put your name on, because that is literally what
          happens: your name goes into the published receipt as the approver, and
          nothing publishes without it. This is the only screen that can publish.
        </p>

        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {blocks.map((block) => {
            const isApproved = approved.has(block.n);
            const model =
              block.attempts.at(-1)?.model ?? "—";
            return (
              <div
                key={block.n}
                style={{
                  border: "1px solid var(--color-divider)",
                  background: "var(--color-surface)",
                  padding: 14,
                  display: "flex",
                  gap: 16,
                }}
              >
                {block.still_uri ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={block.still_uri}
                    alt={`Block ${block.n}`}
                    style={{ width: 72, aspectRatio: "9/16", objectFit: "cover", flex: "none" }}
                  />
                ) : (
                  <div
                    style={{
                      width: 72,
                      aspectRatio: "9/16",
                      flex: "none",
                      background: "var(--color-neutral-300)",
                    }}
                  />
                )}

                <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 6 }}>
                  <span className="mono" style={{ fontSize: 10, color: "var(--color-neutral-600)" }}>
                    BLOCK {block.n} · {model}
                    {block.voice_duration_s ? ` · ${block.voice_duration_s.toFixed(1)}s` : ""}
                    {block.fact_ids.length > 0 ? ` · ${block.fact_ids.join(" ")}` : ""}
                  </span>
                  <p style={{ fontSize: 13, margin: 0 }}>{block.narration}</p>
                  <div style={{ display: "flex", gap: 8, marginTop: "auto", alignItems: "center" }}>
                    <button
                      type="button"
                      className="btn btn-secondary"
                      style={{ fontSize: 12, padding: "4px 10px" }}
                      onClick={() => toggle(block.n)}
                    >
                      {isApproved ? "Undo" : "Approve"}
                    </button>
                    {block.clip_uri && (
                      <a
                        className="btn btn-ghost"
                        style={{ fontSize: 12 }}
                        href={block.clip_uri}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Watch ↗
                      </a>
                    )}
                  </div>
                </div>

                {isApproved && (
                  <span style={{ alignSelf: "center" }}>
                    <Stamp kind="approved" label="Approved" />
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div
        className="card elev-md"
        style={{ alignSelf: "start", position: "sticky", top: 0, gap: 14, padding: 20 }}
      >
        <span className="card-kicker">Approval panel</span>

        <div className="field">
          <label htmlFor="approver">Your name</label>
          <input
            id="approver"
            className="input mono"
            style={{ fontSize: 12 }}
            placeholder="m.okafor"
            value={approver}
            onChange={(e) => setApprover(e.target.value)}
          />
        </div>

        <div
          className="mono"
          style={{ fontSize: 12, display: "flex", flexDirection: "column", gap: 6 }}
        >
          {blocks.map((b) => (
            <div key={b.n}>
              <span style={{ color: approved.has(b.n) ? "#2b5da8" : "var(--color-neutral-400)" }}>
                {approved.has(b.n) ? "■" : "□"}
              </span>{" "}
              B{b.n} {approved.has(b.n) ? "approved" : "pending"}
            </div>
          ))}
        </div>

        <div className="hr" style={{ margin: "4px 0" }} />

        <input
          className="input mono"
          style={{ fontSize: 12 }}
          placeholder="access code"
          value={accessCode}
          onChange={(e) => setAccessCode(e.target.value)}
          aria-label="Access code"
        />

        <button
          type="button"
          onClick={stamp}
          disabled={!canStamp}
          className="anton"
          style={{
            border: "3.5px solid #2b5da8",
            color: "#2b5da8",
            background: "transparent",
            fontSize: 22,
            textAlign: "center",
            padding: 12,
            transform: "rotate(-1.5deg)",
            // Faded until it is reachable. The mockup shows it at .45 and that
            // is the honest state: it is not a button yet.
            opacity: canStamp ? 1 : 0.45,
            cursor: canStamp ? "pointer" : "not-allowed",
            textTransform: "uppercase",
            letterSpacing: ".05em",
          }}
        >
          {busy ? "Stamping…" : "Stamp: Approved"}
        </button>

        <p className="mono" style={{ fontSize: 10.5, color: "var(--color-neutral-600)", margin: 0 }}>
          Your name and this timestamp become part of the video&apos;s permanent record.
        </p>

        {!allSeen && (
          <p className="mono" style={{ fontSize: 10.5, color: "var(--color-neutral-600)", margin: 0 }}>
            Approve every block first — {blocks.length - approved.size} left.
          </p>
        )}

        {alreadyPublished && (
          <p className="mono" style={{ fontSize: 10.5, color: "var(--color-accent-700)", margin: 0 }}>
            This run is already published. Stamping again re-cuts it and replaces
            the approver on the record.
          </p>
        )}

        {problem && (
          <p className="mono" style={{ fontSize: 11, color: "var(--color-accent-700)", margin: 0 }}>
            {problem}
          </p>
        )}
      </div>
    </div>
  );
}

/** Rebuild the posted story from the run's own facts.
 *
 *  The worker re-parses on every call, so assembly cannot be reached with a
 *  story that would not survive Wall 1 — there is no privileged path in. */
function storyFromRun(run: RunState) {
  return {
    id: run.run_id,
    title: run.story,
    through_line: String(run.art_direction?.through_line ?? "tower-signal"),
    // Absent on runs from before kits existed — those were all house.
    kit: String(run.art_direction?.kit ?? "house"),
    facts: run.facts.map((f) => ({
      text: f.text,
      sources: f.sources.map((s) =>
        s.kind === "url" ? { url: s.value } : { citation: s.value },
      ),
    })),
  };
}
