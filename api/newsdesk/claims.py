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

**Scope, stated rather than implied.** This catches unsourced *quantities*.
A qualitative fabrication ("stations closed in protest") passes here; POL-1 and
the human at Wall 3 are what stand between that and air. Claiming otherwise
would be the more dangerous error.
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


@dataclass(frozen=True)
class Problem:
    """One reason a block cannot proceed. Written for a journalist to act on."""

    block: int
    kind: str  # unknown_fact | evidence_missing | spoken_missing | unmapped_number
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

    orphans = number_phrases(covered)
    if orphans:
        listed = ", ".join(f"\"{o.strip()}\"" for o in dict.fromkeys(orphans))
        problems.append(Problem(
            block.n, "unmapped_number",
            f"this line states {listed} without tracing to a fact. Map it or cut it — "
            f"a number on screen is a claim.",
        ))

    return tuple(problems)


def validate_script(story: Story, blocks: tuple[ScriptBlock, ...]) -> ScriptResult:
    """Wall 1 applied to the script: no claim on screen without a fact behind it."""
    return ScriptResult(problems=tuple(p for b in blocks for p in validate_block(story, b)))
