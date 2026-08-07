/** Translate a gate refusal into something a journalist can act on.
 *
 *  The raw refusal is receipt language — rule ids, word windows, attempt
 *  counts — and it stays visible because the record is the product. This
 *  module reads that text and produces the working-language version: what
 *  happened in plain words, and concrete suggestions computed from the
 *  journalist's own facts. Suggestions are only ever suggestions; nothing
 *  here edits a fact. The Apply button in the wizard does that, visibly,
 *  as a user action.
 */

export interface FactTrim {
  index: number;
  words: number;
  suggestion: string;
}

export interface RefusalHelp {
  headline: string;
  tips: string[];
  trims: FactTrim[];
}

const wordCount = (text: string): number => text.trim().split(/\s+/).filter(Boolean).length;

/** First sentence of a fact, as the mechanical shortening suggestion. */
const firstSentence = (text: string): string => {
  const match = text.trim().match(/^.*?[.!?](?=\s|$)/);
  return (match ? match[0] : text).trim();
};

export function explainRefusal(problem: string, facts: { text: string }[]): RefusalHelp | null {
  const tips: string[] = [];
  let headline = "";

  const tooLong = /POL-5 — \d+ words \(need 23-27\)/.test(problem);
  const badSentenceCount = /\d+ sentences? \(need 2-3\)/.test(problem);
  const untraced = problem.match(/states "([^"]+)" without tracing to a fact/);
  const badMapping = /the mapping quotes .* which is not in this line/i.test(problem);

  if (tooLong || badSentenceCount) {
    headline =
      "The script kept coming out the wrong length for the narrator. Each beat is ten seconds, which fits 23 to 27 spoken words, and the draft kept running long.";
    tips.push(
      "Long or number-dense facts push the script long. Shortening your longest facts almost always fixes it.",
    );
  }
  if (untraced) {
    if (!headline)
      headline = `The draft said "${untraced[1]}", but none of your facts contain it. A number or claim on screen has to trace to a fact.`;
    tips.push(
      `If "${untraced[1]}" belongs in the story, add it as a fact with its source. Otherwise a redraft will usually drop it.`,
    );
  }
  if (badMapping) {
    if (!headline)
      headline =
        "The draft cited one of your facts for a sentence that fact does not actually support. That is the checker doing its job.";
    tips.push("This one is usually the model's mistake, and a redraft fixes it without any change from you.");
  }
  if (!headline) return null;

  // Concrete, per-fact suggestions: the longest facts, shortened to their
  // first sentence — shown as previews the journalist can apply or ignore.
  const trims: FactTrim[] = facts
    .map((f, index) => ({ index, words: wordCount(f.text), suggestion: firstSentence(f.text) }))
    .filter((t) => t.words > 27 && t.suggestion !== facts[t.index].text.trim())
    .sort((a, b) => b.words - a.words)
    .slice(0, 2);

  return { headline, tips, trims: tooLong || badSentenceCount ? trims : [] };
}
