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

import {
  Draft,
  DraftFact,
  PROBLEM_TEXT,
  emptyFact,
  factId,
  factProblem,
  sourceLabel,
  sourcedCount,
} from "@/lib/draft";

export function FactsAndSources({
  draft,
  onChange,
  onNext,
  ready,
}: {
  draft: Draft;
  onChange: (next: Draft) => void;
  onNext: () => void;
  ready: boolean;
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
