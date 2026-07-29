/** The story a journalist is composing, before it becomes a run.
 *
 *  Deliberately the same shape `newsdesk/storyfile.py` parses, and deliberately
 *  NOT a second source of truth about what is valid. The server refuses an
 *  unsourced fact whatever this file says; these checks exist so the refusal
 *  arrives while the cursor is still in the box, not after a round trip.
 *
 *  Where the two could drift, the rule is copied with the reason attached — see
 *  `looksLikeUrl`, which is the one place the frontend has to know something
 *  slightly awkward about the backend's taste.
 */

export type DraftSource = { kind: "url" | "citation"; value: string };
export type DraftFact = { id: string; text: string; sources: DraftSource[] };

export type Draft = {
  title: string;
  throughLine: string;
  facts: DraftFact[];
};

/** F1, F2… assigned by position, exactly as `Story.build` does it.
 *  Claim mapping cites these, so the order on screen IS the order in the
 *  receipt — reordering facts renumbers them and that is not a bug. */
export function factId(index: number): string {
  return `F${index + 1}`;
}

export function emptyFact(): DraftFact {
  return { id: crypto.randomUUID(), text: "", sources: [] };
}

export function emptyDraft(): Draft {
  return { title: "", throughLine: "tower-signal", facts: [emptyFact()] };
}

/** http(s) only.
 *
 *  The backend refuses a bare source string that is not a URL, and says to
 *  write it as a citation instead. That looks pedantic until you see why:
 *  "npr.org (Aug 1, 2025)" is a citation, and promoting it to a link would put
 *  a dead hyperlink in the public receipt that reads like a live source. So the
 *  UI offers the two kinds explicitly rather than guessing. */
export function looksLikeUrl(value: string): boolean {
  return /^https?:\/\/\S+$/i.test(value.trim());
}

export type FactProblem = "empty" | "unsourced" | "bad-url" | null;

export function factProblem(fact: DraftFact): FactProblem {
  if (!fact.text.trim()) return "empty";
  if (fact.sources.length === 0) return "unsourced";
  const badUrl = fact.sources.some(
    (s) => s.kind === "url" && !looksLikeUrl(s.value),
  );
  return badUrl ? "bad-url" : null;
}

export const PROBLEM_TEXT: Record<NonNullable<FactProblem>, string> = {
  empty: "A fact needs text before it can be sourced.",
  // Wall 1, in the journalist's words rather than the system's.
  unsourced: "Every fact needs a source before it can appear on screen.",
  "bad-url": "A url source has to start with http:// or https://.",
};

/** Whether step 1 can hand off to step 2. */
export function factsReady(draft: Draft): boolean {
  return (
    draft.title.trim().length > 0 &&
    draft.facts.length > 0 &&
    draft.facts.every((f) => factProblem(f) === null)
  );
}

export function sourcedCount(draft: Draft): number {
  return draft.facts.filter((f) => f.sources.length > 0 && f.text.trim()).length;
}

/** A short label for the ledger — the host for a url, the text for a citation. */
export function sourceLabel(source: DraftSource): string {
  if (source.kind !== "url") return source.value;
  try {
    return new URL(source.value).hostname.replace(/^www\./, "");
  } catch {
    return source.value;
  }
}

/** Slug used as the run id and the B2 prefix.
 *
 *  Must satisfy the backend's `_ID_CHARS` — lowercase, digits, hyphens — or the
 *  post is refused. Generated from the title rather than asked for, because a
 *  journalist should not have to think about storage keys. */
export function slugify(title: string): string {
  const base = title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 40);
  return base || "story";
}

/** The exact JSON `POST /runs` expects — the same document shape as a
 *  `stories/*.yaml` file, because the server parses both with one parser. */
export function toPayload(draft: Draft, slug: string) {
  return {
    id: slug,
    title: draft.title.trim(),
    through_line: draft.throughLine,
    facts: draft.facts.map((f) => ({
      text: f.text.trim(),
      sources: f.sources.map((s) =>
        s.kind === "url" ? { url: s.value.trim() } : { citation: s.value.trim() },
      ),
    })),
  };
}
