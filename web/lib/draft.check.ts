/** Runnable check for `draft.ts` — `bun lib/draft.check.ts` from `web/`.
 *
 *  The web app has no test runner and this is not an argument for adding one
 *  the week of a deadline. It is an argument for the two rules below not being
 *  trusted to a reading: both were wrong in the version that shipped Wall 1,
 *  and both were found by driving the real UI rather than by looking at code.
 */

import {
  factProblem,
  slugify,
  sourcedCount,
  type DraftFact,
} from "./draft";

let failed = 0;

function eq(actual: unknown, expected: unknown, what: string): void {
  const ok = JSON.stringify(actual) === JSON.stringify(expected);
  if (!ok) {
    failed += 1;
    console.error(
      `FAIL  ${what}\n      got ${JSON.stringify(actual)}, want ${JSON.stringify(expected)}`,
    );
  }
}

const fact = (text: string, sources: DraftFact["sources"]): DraftFact => ({
  id: "check",
  text,
  sources,
});

// --- slugify: the run id is printed on the receipt and is the B2 prefix ------

eq(
  slugify("What a billion dollars of vinyl says about 2025"),
  "what-a-billion-dollars-of-vinyl-says",
  "a title past the limit is cut back to a whole word",
);
eq(
  slugify("Who pays when public radio goes dark?"),
  "who-pays-when-public-radio-goes-dark",
  "a title inside the limit keeps its last word",
);
eq(slugify("!!!"), "story", "a title with no letters still yields an id");
eq(
  slugify("a".repeat(60)).length,
  40,
  "one word longer than the limit is cut hard — a run needs an id",
);

// --- factProblem: an empty box is not a source ------------------------------

eq(
  factProblem(fact("a fact", [{ kind: "citation", value: "" }])),
  "unsourced",
  "a blank citation row does not source a fact",
);
eq(
  factProblem(fact("a fact", [{ kind: "citation", value: "   " }])),
  "unsourced",
  "whitespace does not source a fact",
);
eq(
  factProblem(fact("a fact", [])),
  "unsourced",
  "no rows at all is still unsourced",
);
eq(
  factProblem(fact("a fact", [{ kind: "citation", value: "RIAA, 2025" }])),
  null,
  "a written citation sources a fact",
);
eq(
  factProblem(fact("a fact", [{ kind: "url", value: "npr.org" }])),
  "bad-url",
  "a bare host is still refused as a link",
);

eq(
  sourcedCount({
    title: "t",
    throughLine: "record",
    facts: [
      fact("a", [{ kind: "citation", value: "" }]),
      fact("b", [{ kind: "citation", value: "RIAA, 2025" }]),
    ],
  }),
  1,
  "the sources ledger counts filled rows, not slots",
);

if (failed > 0) {
  console.error(`\n${failed} check(s) failed`);
  process.exit(1);
}
console.log("draft.ts — all checks passed");
