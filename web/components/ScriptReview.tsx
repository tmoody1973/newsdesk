"use client";

/**
 * Wizard step 3 — mockup 1h.
 *
 * The script the model wrote, with what it cost the journalist to trust it:
 * every block shows the facts its claims trace to. A block that traces to
 * nothing turns coral and says so, which is the same treatment step 1 gives an
 * unsourced fact — the rule is one rule, and it should look like one rule.
 *
 * Read-only on purpose in this pass. Editing a line here would silently break
 * the claim map that was validated against it, and the honest repair is a
 * re-run rather than a textarea. Said out loud rather than left as a mystery
 * disabled field.
 */

import type { Block } from "@/lib/types";

const WORDS_MIN = 23;
const WORDS_MAX = 27;

function words(text: string): number {
  return text.trim().split(/\s+/).filter(Boolean).length;
}

export function ScriptReview({
  blocks,
  onSend,
  sending,
}: {
  blocks: Block[];
  onSend: () => void;
  sending: boolean;
}) {
  // The kicker is allowed to be pure framing — it is the closing image, and
  // demanding a citation for "The tower still stands" is how a validator that
  // fires on everything gets switched off. Every other block is reporting.
  //
  // This mirrors `claims.py`'s `untraced_block` rule rather than duplicating a
  // judgement: since 2026-07-28 the backend refuses these during generation, so
  // by the time a script reaches this screen it should already be clean. The
  // check stays as a belt — a script generated before the rule landed, or
  // resumed from older state, would otherwise slip through.
  const untraced = blocks
    .slice(0, -1)
    .filter((b) => b.fact_ids.length === 0);

  return (
    <div
      style={{
        padding: "32px 36px 0",
        maxWidth: 900,
        display: "flex",
        flexDirection: "column",
        gap: 14,
      }}
    >
      {blocks.map((block, i) => (
        <BlockCard key={block.n} block={block} isKicker={i === blocks.length - 1} />
      ))}

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          borderTop: "2px solid var(--color-divider)",
          paddingTop: 16,
        }}
      >
        <span className="mono" style={{ fontSize: 11, color: "var(--color-neutral-600)" }}>
          {blocks.length} blocks ·{" "}
          {untraced.length === 0
            ? "every claim traces to a fact"
            : `${untraced.length} block${untraced.length > 1 ? "s" : ""} trace nothing`}
        </span>
        {/* Blocked while any block traces nothing.
            The backend's `unmapped_assertion` rule is sentence-scoped: a block
            whose lines carry NO claim at all is read as framing and passes. That
            is right for a closing image and wrong for a whole evidence block, and
            it leaves the model a way out — assert nothing traceable and nothing
            objects. Until the backend requires a claim per non-kicker block, this
            is where that hole is closed, and it is closed in the direction the
            product argues for. */}
        <button
          type="button"
          className="btn btn-primary"
          disabled={sending || blocks.length === 0 || untraced.length > 0}
          onClick={onSend}
        >
          {sending ? "Sending…" : "Send to generation"}
        </button>
      </div>
    </div>
  );
}

function BlockCard({ block, isKicker }: { block: Block; isKicker: boolean }) {
  const n = words(block.narration);
  const traced = block.fact_ids.length > 0 || isKicker;
  const offLength = n < WORDS_MIN || n > WORDS_MAX;

  return (
    <div
      style={{
        border: `1px solid ${traced ? "var(--color-divider)" : "var(--color-accent)"}`,
        background: traced ? "var(--color-surface)" : "var(--color-accent-100)",
        padding: 16,
        display: "flex",
        flexDirection: "column",
        gap: 10,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <span
          className="mono"
          style={{
            fontSize: 11,
            color: traced ? "var(--color-neutral-600)" : "var(--color-accent-700)",
          }}
        >
          BLOCK {block.n}
        </span>
        <span
          className="mono"
          style={{
            fontSize: 11,
            color: offLength ? "var(--color-accent-700)" : "var(--color-neutral-600)",
          }}
        >
          {n} words
          {block.voice_duration_s ? ` · ${block.voice_duration_s.toFixed(1)}s` : ""}
        </span>
      </div>

      <p style={{ fontSize: 14, margin: 0, lineHeight: 1.55 }}>{block.narration}</p>

      <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        {traced ? (
          block.fact_ids.map((id) => (
            <span
              key={id}
              className="mono tag"
              style={{ background: "#dde6f2", color: "#2b5da8", fontSize: 11 }}
            >
              {id}
            </span>
          ))
        ) : (
          <>
            <span
              className="mono tag"
              style={{ background: "var(--color-accent)", color: "#fff", fontSize: 11 }}
            >
              ?
            </span>
            <span className="mono" style={{ fontSize: 11, color: "var(--color-accent-700)" }}>
              This block is reporting and traces to no fact. Only the kicker may
              be pure framing.
            </span>
          </>
        )}
      </div>

      {/* The claim map, in the journalist's terms: the phrase they will hear,
          and the words in the fact that stand behind it. This is the thing the
          receipt asserts publicly, so it should not first be seen in public. */}
      {block.claims.length > 0 && (
        <details>
          <summary
            className="mono"
            style={{ fontSize: 11, color: "var(--color-neutral-600)", cursor: "pointer" }}
          >
            {block.claims.length} claim{block.claims.length > 1 ? "s" : ""} traced
          </summary>
          <div
            className="mono"
            style={{
              fontSize: 11,
              display: "flex",
              flexDirection: "column",
              gap: 6,
              marginTop: 8,
              paddingLeft: 12,
              borderLeft: "2px solid var(--color-divider)",
            }}
          >
            {block.claims.map((c, i) => (
              <div key={i}>
                <span style={{ color: "#2b5da8" }}>{c.fact_id}</span>{" "}
                <span>&ldquo;{c.spoken}&rdquo;</span>
                <div style={{ color: "var(--color-neutral-600)" }}>↳ {c.evidence}</div>
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}
