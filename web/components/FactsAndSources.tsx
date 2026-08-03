"use client";

/**
 * Wizard step 1 — mockup 1f.
 *
 * "Every claim starts here." The heading is the product's argument, so the
 * screen has to earn it: an unsourced fact is not a validation error tucked
 * under a field, it turns the whole card coral and says the rule in plain
 * words. That is the mockup's own choice and it is the right one — this is the
 * moment the tool tells a journalist what it will not do.
 *
 * The layout is the mockup's: 1fr / 340px, facts left, sources ledger right.
 */

import { useState } from "react";

import {
  Draft,
  DraftFact,
  PROBLEM_TEXT,
  emptyFact,
  factId,
  factProblem,
  filledSources,
  looksLikeUrl,
  sourceLabel,
  sourcedCount,
} from "@/lib/draft";
import { FactProposal, WorkerError, ingestUrl } from "@/lib/worker";

export function FactsAndSources({
  draft,
  onChange,
  onNext,
  ready,
  accessCode,
  onAccessCode,
}: {
  draft: Draft;
  onChange: (next: Draft) => void;
  onNext: () => void;
  ready: boolean;
  accessCode: string;
  onAccessCode: (next: string) => void;
}) {
  function patch(i: number, changes: Partial<DraftFact>) {
    onChange({
      ...draft,
      facts: draft.facts.map((f, j) => (j === i ? { ...f, ...changes } : f)),
    });
  }

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "1fr 340px",
        gap: 32,
        padding: "32px 36px 0",
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        <h2 style={{ fontSize: 24, margin: 0 }}>Every claim starts here.</h2>

        <div className="field">
          <label htmlFor="story-title">What is this story about?</label>
          <input
            id="story-title"
            className="input"
            placeholder="Who pays when public radio goes dark?"
            value={draft.title}
            onChange={(e) => onChange({ ...draft, title: e.target.value })}
          />
        </div>

        <PullFromUrl
          facts={draft.facts}
          accessCode={accessCode}
          onAccessCode={onAccessCode}
          onConfirm={(fact) =>
            onChange({
              ...draft,
              // A first pull otherwise lands next to the blank row every draft
              // opens with, and the screen answers a successful pull with a red
              // UNSOURCED tag and a dead "Check sources". A row nobody has typed
              // in is a slot, not a fact — the confirmed one takes the slot.
              facts: isBlank(draft.facts) ? [fact] : [...draft.facts, fact],
            })
          }
        />

        {draft.facts.map((fact, i) => (
          <FactCard
            key={fact.id}
            fact={fact}
            label={factId(i)}
            onPatch={(changes) => patch(i, changes)}
            onRemove={
              draft.facts.length > 1
                ? () =>
                    onChange({
                      ...draft,
                      facts: draft.facts.filter((_, j) => j !== i),
                    })
                : undefined
            }
          />
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
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() =>
              onChange({ ...draft, facts: [...draft.facts, emptyFact()] })
            }
          >
            Add fact
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={!ready}
            onClick={onNext}
          >
            Check sources
          </button>
        </div>
      </div>

      <SourcesLedger draft={draft} />
    </div>
  );
}

/** An untouched draft: the single blank row `emptyDraft()` opens with, nothing
 *  typed and no source slot filled. */
function isBlank(facts: DraftFact[]): boolean {
  return (
    facts.length === 1 &&
    !facts[0].text.trim() &&
    filledSources(facts[0]).length === 0
  );
}

/** Paste a link, read what the model proposes, confirm the ones you stand
 *  behind.
 *
 *  Nothing here writes a fact by itself. A proposal shows the sentence it came
 *  from, verbatim, because the only thing that makes a pulled fact usable is a
 *  journalist having read the line it was pulled from — a paraphrase with a
 *  confident tick next to it is exactly what this tool exists not to produce. */
function PullFromUrl({
  facts,
  accessCode,
  onAccessCode,
  onConfirm,
}: {
  facts: DraftFact[];
  accessCode: string;
  onAccessCode: (next: string) => void;
  onConfirm: (fact: DraftFact) => void;
}) {
  const [url, setUrl] = useState("");
  const [pulling, setPulling] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [result, setResult] = useState<{
    /** The URL these proposals were pulled from, frozen at pull time. The
     *  input keeps taking keystrokes afterwards, and a proposal must never be
     *  sourced to a link its quote was not checked against — that would put a
     *  URL in the public receipt that nothing was verified from. */
    url: string;
    proposals: FactProposal[];
    dropped: number;
  } | null>(null);

  async function pull() {
    setPulling(true);
    setProblem(null);
    setResult(null);
    const pulledFrom = url.trim();
    try {
      const pulled = await ingestUrl(pulledFrom, accessCode);
      setResult({
        url: pulledFrom,
        proposals: pulled.proposals ?? [],
        dropped: pulled.dropped ?? 0,
      });
    } catch (err) {
      // The server's refusal already names the fallback — "paste the text of
      // the story instead". Rewording it would drop the only instruction in it.
      setProblem(err instanceof WorkerError ? err.message : String(err));
    } finally {
      setPulling(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div className="field">
        <label htmlFor="ingest-url">Paste a link to a story you reported.</label>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <input
            id="ingest-url"
            className="input mono"
            style={{ fontSize: 12, color: "#2b5da8" }}
            placeholder="https://npr.org/2025/08/01/cpb-rescission"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
          <input
            className="input mono"
            style={{ width: 140, fontSize: 12 }}
            placeholder="access code"
            value={accessCode}
            onChange={(e) => onAccessCode(e.target.value)}
            aria-label="Access code"
          />
          <button
            type="button"
            className="btn btn-secondary"
            style={{ flex: "none" }}
            disabled={!looksLikeUrl(url) || pulling}
            onClick={pull}
          >
            {pulling ? "Pulling…" : "Pull facts"}
          </button>
        </div>
      </div>

      {problem && (
        <p
          className="mono"
          style={{
            fontSize: 11,
            color: "var(--color-accent-700)",
            margin: 0,
            whiteSpace: "pre-wrap",
          }}
        >
          {problem}
        </p>
      )}

      {result && (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <span className="card-kicker">
            Proposed facts — nothing is added until you add it
          </span>

          {result.proposals.map((proposal, i) => {
            // Read off the draft rather than remembered here, so removing the
            // confirmed row hands the proposal back instead of stranding it at
            // ADDED. The trade: editing a confirmed fact's text re-enables its
            // button and lets it be added twice — both rows are on screen, so
            // that failure is one a journalist can see and delete.
            const source = proposal.url || result.url;
            const isAdded = facts.some((f) => f.text === proposal.text);
            return (
              <div
                key={i}
                className="card"
                style={{ border: "1px solid var(--color-divider)", gap: 8 }}
              >
                <p style={{ fontSize: 14, margin: 0 }}>{proposal.text}</p>
                <p
                  className="mono"
                  style={{
                    fontSize: 11,
                    margin: 0,
                    color: "var(--color-neutral-600)",
                    borderLeft: "2px solid var(--color-divider)",
                    paddingLeft: 10,
                  }}
                >
                  &ldquo;{proposal.quote}&rdquo;
                </p>
                <div className="card-meta" style={{ justifyContent: "space-between" }}>
                  <span className="mono" style={{ fontSize: 11, color: "#2b5da8" }}>
                    {sourceLabel({ kind: "url", value: source })}
                  </span>
                  {isAdded ? (
                    <span
                      className="tag tag-neutral mono"
                      style={{ fontSize: 10, letterSpacing: ".06em" }}
                    >
                      ADDED
                    </span>
                  ) : (
                    <button
                      type="button"
                      className="btn btn-secondary"
                      style={{ fontSize: 12 }}
                      onClick={() =>
                        onConfirm({
                          ...emptyFact(),
                          text: proposal.text,
                          sources: [{ kind: "url", value: source }],
                        })
                      }
                    >
                      Add fact
                    </button>
                  )}
                </div>
              </div>
            );
          })}

          {result.proposals.length === 0 && (
            <span className="card-meta mono">
              Nothing on that page could be quoted verbatim. Type the facts yourself.
            </span>
          )}

          {result.dropped > 0 && (
            <span className="card-meta mono">
              {result.dropped} proposals were dropped because their quotes could not be
              verified against the page.
            </span>
          )}
        </div>
      )}

      <div className="hr" style={{ margin: 0 }} />
    </div>
  );
}

function FactCard({
  fact,
  label,
  onPatch,
  onRemove,
}: {
  fact: DraftFact;
  label: string;
  onPatch: (changes: Partial<DraftFact>) => void;
  onRemove?: () => void;
}) {
  const problem = factProblem(fact);
  // `empty` is the untouched state of a brand-new row. Shouting at someone for
  // not having typed yet is how a validator teaches people to ignore it.
  const angry = problem !== null && problem !== "empty";

  return (
    <div
      style={{
        border: `1px solid ${angry ? "var(--color-accent)" : "var(--color-divider)"}`,
        background: angry ? "var(--color-accent-100)" : "var(--color-surface)",
        padding: 16,
        display: "flex",
        flexDirection: "column",
        gap: 10,
      }}
    >
      <div style={{ display: "flex", gap: 10, alignItems: "baseline" }}>
        <span
          className="mono"
          style={{
            fontSize: 12,
            fontWeight: 500,
            color: angry ? "var(--color-accent-700)" : "#2b5da8",
          }}
        >
          {label}
        </span>
        <textarea
          className="input"
          style={{ minHeight: 56 }}
          placeholder="One verified statement, as you would say it out loud."
          value={fact.text}
          onChange={(e) => onPatch({ text: e.target.value })}
        />
        {onRemove && (
          <button
            type="button"
            className="btn btn-ghost"
            style={{ fontSize: 12 }}
            onClick={onRemove}
            aria-label={`Remove ${label}`}
          >
            Remove
          </button>
        )}
      </div>

      <div style={{ paddingLeft: 32, display: "flex", flexDirection: "column", gap: 8 }}>
        {fact.sources.map((source, i) => (
          <div key={i} style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <span className="mono" style={{ fontSize: 11, color: "var(--color-neutral-600)" }}>
              {source.kind === "url" ? "src:" : "cite:"}
            </span>
            <input
              className="input mono"
              style={{ fontSize: 12, color: "#2b5da8" }}
              placeholder={
                source.kind === "url"
                  ? "https://npr.org/2025/08/01/cpb-rescission"
                  : "RIAA year-end report, 2025"
              }
              value={source.value}
              onChange={(e) =>
                onPatch({
                  sources: fact.sources.map((s, j) =>
                    j === i ? { ...s, value: e.target.value } : s,
                  ),
                })
              }
            />
            <button
              type="button"
              className="btn btn-ghost"
              style={{ fontSize: 12 }}
              onClick={() =>
                onPatch({ sources: fact.sources.filter((_, j) => j !== i) })
              }
              aria-label="Remove source"
            >
              ×
            </button>
          </div>
        ))}

        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {fact.sources.length === 0 && (
            <span
              className="tag mono"
              style={{
                background: "var(--color-accent)",
                color: "#fff",
                fontSize: 10,
                letterSpacing: ".06em",
              }}
            >
              UNSOURCED
            </span>
          )}
          {/* Two buttons rather than one box that guesses. A citation promoted to
              a link is a dead hyperlink in the public receipt that reads live. */}
          <button
            type="button"
            className="btn btn-ghost"
            style={{ fontSize: 12 }}
            onClick={() =>
              onPatch({ sources: [...fact.sources, { kind: "url", value: "" }] })
            }
          >
            + link
          </button>
          <button
            type="button"
            className="btn btn-ghost"
            style={{ fontSize: 12 }}
            onClick={() =>
              onPatch({ sources: [...fact.sources, { kind: "citation", value: "" }] })
            }
          >
            + citation
          </button>
        </div>

        {angry && (
          <p
            className="mono"
            style={{ fontSize: 11, color: "var(--color-accent-700)", margin: 0 }}
          >
            {PROBLEM_TEXT[problem]}
          </p>
        )}
      </div>
    </div>
  );
}

function SourcesLedger({ draft }: { draft: Draft }) {
  const sourced = sourcedCount(draft);
  return (
    <div className="card elev-sm" style={{ alignSelf: "start", gap: 10 }}>
      <span className="card-kicker">Sources ledger</span>
      <div
        className="mono"
        style={{ fontSize: 12, display: "flex", flexDirection: "column", gap: 8 }}
      >
        {draft.facts.map((fact, i) => {
          const bare = fact.sources.length === 0;
          return (
            <div
              key={fact.id}
              style={{
                display: "flex",
                justifyContent: "space-between",
                gap: 12,
                color: bare ? "var(--color-accent)" : undefined,
              }}
            >
              <span>{factId(i)}</span>
              <span
                style={{
                  color: bare ? undefined : "#2b5da8",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {bare ? "— UNSOURCED" : sourceLabel(fact.sources[0])}
              </span>
            </div>
          );
        })}
      </div>
      <div className="hr" style={{ margin: "6px 0" }} />
      <span className="card-meta mono">
        {sourced} of {draft.facts.length} sourced
      </span>
    </div>
  );
}
