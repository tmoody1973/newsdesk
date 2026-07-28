"""The claim->fact validator (MOO-419, P0-2).

A line that states a number the facts do not contain is the failure mode this
whole product exists to prevent, and it is the one a language model produces
most readily — a plausible figure in the right shape, in a script that otherwise
traces cleanly.

Pure functions, no provider access, same discipline as `facts.py` and
`policy/gate.py`. The generator may be wrong; the check may not depend on it.

**How the check avoids parsing numbers.** POL-5 requires numbers spelled out, so
comparing "one point one billion dollars" against "$1.1B" would mean writing a
number parser — and "nineteen sixty-seven" alone breaks the obvious one (a naive
accumulator reads it as eighty-six). Instead the generator declares, per claim,
the phrase as *spoken* in the line and the *evidence* as written in the fact.
Then three string checks do the work:

  1. `spoken` appears in the narration      — the mapping describes this line
  2. `evidence` appears in the cited fact   — the fact actually says it
  3. masking every `spoken` from the line leaves no number-bearing token behind
     — nothing quantitative is unaccounted for

No arithmetic anywhere, so there is no normalization bug to hide behind.

**Scope, widened 2026-07-28 — and the reason why.** This used to catch unsourced
*quantities* only, and said so honestly: "a qualitative fabrication (`stations
closed in protest`) passes here". Then the first story generated through the new
orchestrator produced, in CS-2 block 1:

    "Vinyl revenue hit one point zero four billion dollars. For the first time
     since nineteen eighty-three, records outsold every other physical format
     combined."

Both quantities traced perfectly. "Records outsold every other physical format
combined" is in none of the five facts, and nothing objected. On a tool whose
entire pitch is provenance, "every number traces to a fact" is not the promise
anybody hears — they hear "every claim traces to a fact".

The rule is **sentence-scoped, and that scope is the whole design.** The first
attempt applied content coverage to the entire line, and it was wrong in a way
this file had already warned about: `test_prose_without_numbers_needs_no_claim`
carries the note "a validator that fires on everything gets switched off". Whole-
line coverage flagged the CS-1 kicker — "The tower still stands. What lights it
now is smaller, local, and paid for by the people who happen to live near it" —
which asserts nothing checkable and is exactly the closing image the format
wants. It also produced shards like "already", "took" and "back", which name no
problem a journalist can act on.

What distinguishes the two cases is not the words, it is the company they keep:

  * A sentence carrying **no** mapped claim is rhetorical framing. The human at
    Wall 3 owns it, and always did.
  * A sentence carrying a mapped claim is presenting itself as reporting. Any
    other assertion riding in that sentence is borrowing the credibility of the
    traced one, and has to trace too.

So: mask the accepted claims, then look for surviving content **only in the
sentences that had a claim in them**. No parsing, no arithmetic, no entailment
model — the alphabet stops being free precisely where a number made the sentence
load-bearing.

The practical effect is on the GENERATOR, and it is the intended one: mapping a
bare quantity ("one point zero four billion dollars") no longer accounts for its
sentence, so the model has to map the whole assertion ("vinyl revenue hit one
point zero four billion dollars") and produce verbatim evidence for it. An
assertion no fact supports cannot produce that evidence, and the line goes to a
repair round instead of to air.

**What this still does not do.** It proves *coverage*, not *entailment*. A claim
whose spoken phrase and evidence span are both real can still draw a conclusion
the fact does not support. Only a judge model can test that, and a judge model is
a generator — it can be wrong, and this module's discipline is that the check may
not depend on a generator. Wall 3's human is what stands there. Said plainly here
so the receipt can say it plainly too.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from newsdesk.facts import Story

# Words that carry a quantity on their own. Deliberately excludes "point" and
# "a" — both are ordinary English and would make every line number-bearing.
NUMBER_WORDS = frozenset(
    """
    one two three four five six seven eight nine ten eleven twelve thirteen
    fourteen fifteen sixteen seventeen eighteen nineteen twenty thirty forty
    fifty sixty seventy eighty ninety hundred thousand million billion trillion
    percent half third quarter quarters thirds halves dozen
    first second third fourth fifth sixth seventh eighth ninth tenth
    """.split()
)

_WORD_RE = re.compile(r"[A-Za-z]+(?:-[A-Za-z]+)*|\d[\d,.]*%?")
_WS_RE = re.compile(r"\s+")

# Function words — the glue a sentence needs that asserts nothing on its own.
# Everything NOT here is treated as content, and content left unmapped is an
# unsourced assertion.
#
# The list is deliberately narrow and contains no nouns, no adjectives and no
# lexical verbs. Only auxiliaries and copulas are here ("is", "was", "has"),
# because "revenue was one billion" asserts through its noun and its number,
# not through "was". Adding a verb like "rose" or "fell" to this list would
# silently permit "revenue rose" with no fact behind the direction of travel —
# which is a claim, and a common one.
#
# Discourse adverbs ("however", "meanwhile") are here because they sequence
# rather than assert. "Only", "just" and "still" are NOT: they are rhetorical
# qualifiers that change a fact's meaning ("only two hundred million") and a
# journalist should have to own them.
CONNECTIVES = frozenset(
    """
    a an the this that these those there here
    and or but nor so yet if then than as because while when where whether
    of in on at to from by for with without into onto over under between
    across through during after before since about against per up down out off
    is are was were be been being am
    has have had do does did
    it its they them their theirs he she his her him hers we us our ours
    you your yours i my mine who whom whose which what
    not no
    however meanwhile also too meanwhile instead likewise therefore thus
    now today yesterday tomorrow again
    last next year years month months week weeks day days decade decades ago
    """.split()
)

# A residual phrase shorter than this is tokenization residue, not an assertion.
#
# Measured, 2026-07-28: the first live CS-2 run under this rule failed after
# four repair attempts on "marked" and "last year" — one a copula-ish verb, the
# other a time reference. Neither is a fabricated claim, and neither is
# something a journalist can act on. An assertion needs a subject and a
# predicate, so it is at least two content words; the temporal vocabulary above
# exists so "last year" collapses to nothing rather than being counted.
#
# The cost of the floor, stated rather than discovered: a two-word fabrication
# with no time words in it ("profits doubled") is exactly at the boundary and
# IS still caught, but a one-word one is not. One content word alone cannot
# carry a checkable assertion, so that is the right place to stop.
MIN_ASSERTION_TOKENS = 2

# Words that sit *inside* a spoken quantity without carrying one themselves.
# "point" is here rather than in NUMBER_WORDS for that reason: it makes
# "two point six billion" one phrase, but never makes "the point of the cut"
# a number.
_JOINERS = frozenset({"point", "and", "a", "of", "per"})


def normalize(text: str) -> str:
    """Lowercase with runs of whitespace collapsed.

    Punctuation is preserved on purpose. Stripping it would let "$1.1B" match
    against an unrelated "11b" somewhere in a fact, which is exactly the kind of
    accidental pass this module exists to refuse.
    """
    return _WS_RE.sub(" ", text.strip().lower())


def number_tokens(text: str) -> tuple[str, ...]:
    """Tokens in `text` that assert a quantity.

    A token qualifies if it contains a digit, or if it — or any hyphen-joined
    part of it — is a number word. "forty-eight" qualifies through its parts;
    "1,500" and "48%" through their digits.
    """
    return tuple(t for t in _WORD_RE.findall(text.lower()) if _is_number_token(t))


def _is_number_token(token: str) -> bool:
    if any(ch.isdigit() for ch in token):
        return True
    return any(part in NUMBER_WORDS for part in token.lower().split("-"))


def number_phrases(text: str) -> tuple[str, ...]:
    """Contiguous quantities, as spoken.

    `number_tokens` is what the check needs; this is what the *message* needs.
    Telling a journalist their line states "two", "six" and "billion" makes them
    hunt for three problems that are one problem — the phrase is
    "two point six billion", and that is what has to be mapped or cut.
    """
    spans = [(m.group(0), m.start(), m.end()) for m in _WORD_RE.finditer(text)]
    is_num = [_is_number_token(tok) for tok, _, _ in spans]

    phrases: list[str] = []
    i = 0
    while i < len(spans):
        if not is_num[i]:
            i += 1
            continue
        end, j = spans[i][2], i + 1
        while j < len(spans):
            if is_num[j]:
                end, j = spans[j][2], j + 1
            elif spans[j][0].lower() in _JOINERS and j + 1 < len(spans) and is_num[j + 1]:
                j += 1  # a joiner only bridges when a quantity follows it
            else:
                break
        phrases.append(text[spans[i][1] : end])
        i = j
    return tuple(phrases)


@dataclass(frozen=True)
class Claim:
    """One assertion in a narration line, tied to the fact that supports it."""

    spoken: str    # the phrase as it appears in the narration
    fact_id: str   # F1, F2...
    evidence: str  # the supporting text, verbatim from that fact


@dataclass(frozen=True)
class ScriptBlock:
    """One of the six blocks: the line, its role in the formula, its claims."""

    n: int
    narration: str
    role: str = ""
    claims: tuple[Claim, ...] = field(default_factory=tuple)

    @property
    def fact_ids(self) -> tuple[str, ...]:
        """Deduplicated, in first-mention order — what the block card renders."""
        seen: list[str] = []
        for c in self.claims:
            if c.fact_id not in seen:
                seen.append(c.fact_id)
        return tuple(seen)


_SENTENCE_RE = re.compile(r"[^.!?]+[.!?]*")


def _sentences(text: str) -> tuple[str, ...]:
    """Split on terminal punctuation.

    Crude on purpose. The alternative is a sentence tokenizer, and a dependency
    that decides where a claim's blast radius ends should be readable in one
    sitting. Abbreviations would over-split, which fails toward flagging less —
    the safe direction for a rule whose failure mode is firing too often.
    """
    return tuple(s.strip() for s in _SENTENCE_RE.findall(text) if s.strip())


def _is_content_token(token: str) -> bool:
    """A token that asserts something on its own.

    Digit-bearing tokens are excluded here and handled by `number_phrases`, so
    an unmapped quantity gets the sharper "a number on screen is a claim"
    message rather than being folded into a generic assertion complaint.
    """
    if any(ch.isdigit() for ch in token):
        return False
    if token.lower() in CONNECTIVES:
        return False
    # A hyphenated token is content unless every part is a connective.
    return not all(part in CONNECTIVES for part in token.lower().split("-"))


def content_phrases(text: str) -> tuple[str, ...]:
    """Contiguous runs of content, as written.

    Same shape as `number_phrases` and for the same reason: a journalist told
    their line contains "records", "outsold", "physical" and "format" will hunt
    for four problems that are one problem. The phrase is "records outsold every
    other physical format combined", and that is what has to be mapped or cut.

    A run is broken by punctuation as well as by connectives, so a clause that
    was already accounted for does not bridge into one that was not.
    """
    spans = [(m.group(0), m.start(), m.end()) for m in _WORD_RE.finditer(text)]
    phrases: list[str] = []
    start: int | None = None
    end = 0

    for i, (token, lo, hi) in enumerate(spans):
        # Punctuation between this token and the last one ends the clause, so a
        # phrase that was accounted for cannot bridge into one that was not.
        broken = i > 0 and text[spans[i - 1][2]:lo].strip() != ""

        if _is_content_token(token) and not (broken and start is not None):
            if start is None or broken:
                if start is not None:
                    phrases.append(text[start:end])
                start = lo
            end = hi
            continue

        if start is not None:
            phrases.append(text[start:end])
            start = None

    if start is not None:
        phrases.append(text[start:end])
    return tuple(p.strip() for p in phrases if p.strip())


@dataclass(frozen=True)
class Problem:
    """One reason a block cannot proceed. Written for a journalist to act on."""

    block: int
    kind: str  # unknown_fact | evidence_missing | spoken_missing |
               # unmapped_number | unmapped_assertion
    message: str

    def __str__(self) -> str:
        return f"block {self.block}: {self.message}"


@dataclass(frozen=True)
class ScriptResult:
    problems: tuple[Problem, ...]

    @property
    def passed(self) -> bool:
        return not self.problems

    def explain(self) -> str:
        return "\n".join(str(p) for p in self.problems)


def validate_block(story: Story, block: ScriptBlock) -> tuple[Problem, ...]:
    """Every reason one block fails, not just the first.

    All of them, because a journalist fixing one line should not have to
    re-run to discover the next problem in the same line.
    """
    problems: list[Problem] = []
    known = {f.id for f in story.facts}
    line = normalize(block.narration)
    covered = line
    accepted: list[str] = []

    for claim in block.claims:
        if claim.fact_id not in known:
            problems.append(Problem(
                block.n, "unknown_fact",
                f"claim \"{claim.spoken}\" cites {claim.fact_id}, which is not a fact "
                f"in this story. Known facts: {', '.join(sorted(known))}.",
            ))
            continue

        fact = story.by_id(claim.fact_id)
        if normalize(claim.evidence) not in normalize(fact.text):
            problems.append(Problem(
                block.n, "evidence_missing",
                f"claim \"{claim.spoken}\" cites {claim.fact_id}, but {claim.fact_id} "
                f"does not contain \"{claim.evidence}\". Map it to the fact that says "
                f"it, or cut the claim.",
            ))
            continue

        spoken = normalize(claim.spoken)
        if spoken not in line:
            problems.append(Problem(
                block.n, "spoken_missing",
                f"the mapping quotes \"{claim.spoken}\", which is not in this line. "
                f"The mapping has drifted from the narration.",
            ))
            continue

        # Only claims that survived every check may account for their phrase.
        covered = covered.replace(spoken, " ")
        accepted.append(spoken)

    orphans = number_phrases(covered)
    if orphans:
        listed = ", ".join(f"\"{o.strip()}\"" for o in dict.fromkeys(orphans))
        problems.append(Problem(
            block.n, "unmapped_number",
            f"this line states {listed} without tracing to a fact. Map it or cut it — "
            f"a number on screen is a claim.",
        ))

    # Same rule, applied to content rather than digits — but only inside the
    # sentences that a claim made load-bearing. See the module docstring: whole
    # line coverage flags the kicker, and a validator that fires on everything
    # gets switched off.
    assertions: list[str] = []
    for sentence in _sentences(line):
        carried = [s for s in accepted if s in sentence]
        if not carried:
            continue  # rhetorical framing; Wall 3's human owns it
        residue = sentence
        for spoken in carried:
            residue = residue.replace(spoken, " ")
        assertions.extend(
            p for p in content_phrases(residue)
            if len(_WORD_RE.findall(p)) >= MIN_ASSERTION_TOKENS
        )

    if assertions:
        listed = ", ".join(f"\"{a}\"" for a in dict.fromkeys(assertions))
        problems.append(Problem(
            block.n, "unmapped_assertion",
            f"this line asserts {listed} without tracing to a fact. Map the whole "
            f"assertion — not just the number in it — to the fact that supports it, "
            f"or cut it. Everything on screen is a claim.",
        ))

    return tuple(problems)


def validate_script(story: Story, blocks: tuple[ScriptBlock, ...]) -> ScriptResult:
    """Wall 1 applied to the script: no claim on screen without a fact behind it."""
    return ScriptResult(problems=tuple(p for b in blocks for p in validate_block(story, b)))
