"""Six-block script generation (MOO-419, P0-2).

The first of three `chat()` roles that make up the Genblaze Usage story; the
other two are the policy gate's semantic half and post-render vision evaluation.
All three are governance, which is why they route through
`newsdesk/decisions.py::judged()` — `chat()` cannot ride a `Pipeline.step()` and
produces no manifest entry, so without the ledger the receipt would document
every image we made and stay silent on everything we refused (MOO-433).

The generator is untrusted by construction. It proposes; `claims.py` and POL-5
dispose. A script that fails either is returned as no script at all, with the
reason in the ledger — never as a script with a warning attached, because a
warning is something a tired editor clicks past at eleven at night.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Callable

from genblaze_gmicloud.chat import chat

from newsdesk.claims import Claim, ScriptBlock, validate_script
from newsdesk.decisions import Ledger, judged
from newsdesk.facts import Story
from newsdesk.policy.gate import MAX_SENTENCES, MAX_WORDS, MIN_SENTENCES, MIN_WORDS, check_narration
from newsdesk.state import RunState

BLOCK_COUNT = 6

# Overridable because GMI's catalogue is contract-specific — the slug that works
# on one account 404s on another, and that should cost an env line, not a commit.
# Verified against this account's /v1/models on 2026-07-28. Three findings worth
# keeping, all measured with a 16-token probe:
#   deepseek-ai/DeepSeek-V3        not in the catalogue at all (the SDK docstring
#                                  names it; only the dated and .2 variants exist)
#   deepseek-ai/DeepSeek-V3.2      answers, but ~10s for 16 tokens — a six-block
#                                  generation overran a 240s timeout
#   Qwen3.5-397B, openai/gpt-5.1   429, "service temporarily unavailable"
#   deepseek-ai/DeepSeek-V3-0324   2.7s, but never converged on CS-1: it left
#                                  numbers unmapped and oscillated 22/29/22 words
#                                  across repair rounds.
#   anthropic/claude-haiku-4.5     mapped every claim correctly on the FIRST pass
#                                  in every run, and only ever missed on length —
#                                  which the repair loop fixes. This one.
MODEL = os.getenv("NEWSDESK_SCRIPT_MODEL", "anthropic/claude-haiku-4.5")
PROVIDER = "gmicloud"

# chat() defaults to 60s, which a six-block generation overruns on a large model.
# A timeout is recorded as a *reject* by judged(), so too short a value does not
# fail loudly — it fails as a refusal, which reads like the checker working.
TIMEOUT_S = float(os.getenv("NEWSDESK_SCRIPT_TIMEOUT", "240"))

# The six-beat formula, imported from ~/.claude/skills/vox-motion-graphics via
# design spec §6.2 rather than invented here.
ROLES = ("cold open", "stakes", "evidence", "evidence", "turn", "kicker")

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)

# A worked example at the target length. Stating the window as a number is not
# enough — the first live run on DeepSeek-V3-0324 returned 13, 19, 16, 16 and 21
# words against a 23-27 window, because models treat brevity as quality. Showing
# one correct block is what moves it. Deliberately from a different story than
# any fixture, so it cannot be copied into an answer.
_EXAMPLE = (
    "Three hundred thousand households lost their water subsidy in a single "
    "budget cycle. Nobody announced it. The line item simply stopped appearing, "
    "quarter after quarter."
)
_EXAMPLE_WORDS = len(_EXAMPLE.split())
# Derived, never hand-written. The first version of the prompt described this
# example as "two sentences" while it had three — a prompt teaching a rule and
# miscounting it in the same breath.
_EXAMPLE_SENTENCES = len([s for s in re.split(r"[.!?]+", _EXAMPLE) if s.strip()])

# Three repair rounds, then stop. Design spec §6.4 caps retries on the principle
# that repeated identical failures mean the prompt is wrong, not the seed —
# surface it to the editor rather than burning attempts. Cheap here because it
# is text, but the discipline is the same one the video AgentLoop uses.
MAX_ATTEMPTS = 4

# Failures that get no second ask. Each one means the model cited a source that
# does not support what it said, or quoted a line it did not write — an
# integrity failure rather than a craft miss. An unmapped number is deliberately
# NOT here: usually the figure is real and simply undeclared, and the repair
# cannot launder a fabrication because it still has to produce evidence that
# appears verbatim in a fact.
TERMINAL_KINDS = frozenset({"unknown_fact", "evidence_missing", "spoken_missing"})


class ScriptError(ValueError):
    """Raised when the model's reply is not a usable six-block script."""


def build_prompt(story: Story) -> str:
    """The generation prompt. Carries the craft so the caller does not have to.

    The word window is stated with its reason attached. Told only "23-27 words",
    a model optimizes for the count and writes one long sentence — which is the
    exact failure the calibration takes measured: flowing lines run short and
    the take lands under the window.
    """
    facts = "\n".join(f"{f.id}: {f.text}" for f in story.facts)
    return f"""Write a six-block narration script for a short explainer video.

STORY: {story.title}

FACTS — the only things you may assert:
{facts}

BLOCK FORMULA, one block each, in this order:
1. cold open — the most surprising number, stated flat, no adjectives
2. stakes — what the thing was, so the loss means something
3. evidence — a concrete instance
4. evidence — a second, different concrete instance
5. turn — the complication or the reversal
6. kicker — reframes block 1 without repeating its wording

RULES:
- Every block is {MIN_WORDS}-{MAX_WORDS} words across {MIN_SENTENCES}-{MAX_SENTENCES} sentences.
  Both bounds matter. Sentence-end pauses are what fill the ten-second take; a
  single flowing sentence of the right length still runs short and reads as
  out of sync.
- **Count the words in each block before you emit it, and count them again after
  any edit.** {MIN_WORDS}-{MAX_WORDS} is a hard bound, not a target to aim near.
  Both directions fail for the same reason — the take has to land in a ten-second
  slot. Under {MIN_WORDS} leaves silence the editor has to fill; over {MAX_WORDS}
  gets speed-compressed and reads as rushed. A twenty-two-word line and a
  thirty-two-word line are both rejected.
  A block at the correct length looks like this — {_EXAMPLE_WORDS} words,
  {_EXAMPLE_SENTENCES} sentences:
      "{_EXAMPLE}"
  Note how short it is. Resist adding a second clause explaining the
  significance; the picture carries that.
- Spell numbers out as they are spoken: "one point one billion dollars", not "$1.1B".
- Assert nothing that is not in the facts above. Do not compute new figures from
  them — a derived number is an unsourced number.
- For every quantity you state, emit a claim with:
    spoken   — the phrase exactly as it appears in your narration
    fact_id  — the fact it comes from
    evidence — the supporting text copied verbatim from that fact
- Claims are also welcome for non-numeric assertions. Every claim is checked.
- Use every fact at least once across the six blocks. A fact the journalist
  sourced and verified, left on the floor, is research thrown away — and the
  receipt lists it as entered but unused.

Reply with JSON only, no commentary:
{{"blocks": [{{"n": 1, "role": "cold open", "narration": "...",
  "claims": [{{"spoken": "...", "fact_id": "F1", "evidence": "..."}}]}}]}}
"""


def parse_blocks(text: str, *, expect: int | None = BLOCK_COUNT) -> tuple[ScriptBlock, ...]:
    """Parse the model's reply into blocks. Tolerant of fences, strict about shape.

    `expect` is relaxed for repair replies, which return only the blocks that
    needed fixing rather than the whole script.
    """
    fenced = _FENCE_RE.search(text)
    candidate = fenced.group(1) if fenced else text

    # Fall back to the outermost braces — models prepend "Here is the script:"
    # even when told not to, and refusing to cope with that is a self-own.
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError:
        start, end = candidate.find("{"), candidate.rfind("}")
        if start == -1 or end <= start:
            raise ScriptError(
                f"the model did not return JSON. First 200 characters: {text[:200]!r}"
            ) from None
        try:
            payload = json.loads(candidate[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ScriptError(f"the model returned malformed JSON: {exc}") from exc

    raw = payload.get("blocks") if isinstance(payload, dict) else None
    if not isinstance(raw, list):
        raise ScriptError("reply has no 'blocks' list")
    if expect is not None and len(raw) != expect:
        raise ScriptError(f"expected {expect} blocks, got {len(raw)}")

    blocks: list[ScriptBlock] = []
    for i, b in enumerate(raw, start=1):
        try:
            blocks.append(ScriptBlock(
                n=int(b.get("n", i)),
                narration=str(b["narration"]).strip(),
                role=str(b.get("role", ROLES[i - 1])),
                claims=tuple(
                    Claim(
                        spoken=str(c["spoken"]),
                        fact_id=str(c["fact_id"]).upper(),
                        evidence=str(c["evidence"]),
                    )
                    for c in b.get("claims", ())
                ),
            ))
        except (KeyError, TypeError, ValueError) as exc:
            raise ScriptError(f"block {i} is malformed: {exc}") from exc

    return tuple(blocks)


def _pacing_instruction(narration: str) -> str:
    """What to actually do to this line, as a signed word count.

    The first version of the repair prompt only ever said "lengthen", which is
    useless advice to a model writing 32 words against a 23-27 window — and that
    was the exact failure claude-haiku-4.5 hit on the live CS-1 run. The
    direction has to come from the measurement, not from an assumption about
    which way models miss.
    """
    words = len(narration.split())
    sentences = len([s for s in re.split(r"[.!?]+", narration) if s.strip()])

    parts = [f"{words} words, {sentences} sentence{'s' if sentences != 1 else ''}."]
    if words < MIN_WORDS:
        parts.append(f"ADD {MIN_WORDS - words} to {MAX_WORDS - words} words.")
    elif words > MAX_WORDS:
        parts.append(f"CUT {words - MAX_WORDS} to {words - MIN_WORDS} words.")
    if sentences < MIN_SENTENCES:
        parts.append(f"SPLIT into {MIN_SENTENCES}-{MAX_SENTENCES} sentences.")
    elif sentences > MAX_SENTENCES:
        parts.append(f"MERGE down to {MAX_SENTENCES} sentences.")
    return " ".join(parts)


def _repair_prompt(original: str, pacing: list, unmapped: list, failing: list[int]) -> str:
    """Ask for a fix, quoting each line's measured failure.

    Naming the number is what makes this work — "some blocks are too short"
    produces another round of short blocks, while "block 4 is 18 words, add five
    to nine more" produces a fix.
    """
    sections = []

    if pacing:
        misses = "\n".join(
            f"  Block {b.n} ({b.role}) — {_pacing_instruction(b.narration)}\n"
            f"    current: \"{b.narration}\""
            for b, _ in pacing
        )
        sections.append(
            f"These blocks missed the length window:\n\n{misses}\n\n"
            "Where a line is short, lengthen it using detail already present in the "
            "facts — never by adding a new assertion. Where a line is long, cut "
            "qualifiers and restatement, not facts: if a claim has to go, drop its "
            "claim entry too."
        )

    if unmapped:
        listed = "\n".join(f"  {p}" for p in unmapped)
        sections.append(
            f"These lines state a quantity with no claim behind it:\n\n{listed}\n\n"
            "For each one, either add a claim whose evidence is copied verbatim from the "
            "fact that supports it, or remove the quantity from the line. If no fact "
            "contains that figure, remove it — do not invent a source for it."
        )

    body = "\n\n".join(sections)
    listed = ", ".join(str(n) for n in failing)
    return f"""{original}

---

You already answered this once. {body}

Return ONLY block{'s' if len(failing) != 1 else ''} {listed} — {len(failing)} block(s), not
{BLOCK_COUNT}. The others are finished and must not be resent. Same JSON shape as
before, with each block keeping its original "n".
"""


def generate_script(
    state: RunState,
    ledger: Ledger,
    story: Story,
    *,
    model: str = MODEL,
    chat_fn: Callable[..., Any] = chat,
) -> tuple[RunState, Ledger, tuple[ScriptBlock, ...]]:
    """Generate, check, and record. Returns no blocks unless every check passed.

    `chat_fn` is injected so the whole path is testable at $0 with no network.
    That is not only convenience: it is the same property Wall 2 relies on, and
    it means the CS-3 strictness probe runs in CI rather than on a credit card.
    """
    story.validate()  # Wall 1 — nothing unsourced gets as far as a paid call
    prompt = build_prompt(story)
    accepted: list[ScriptBlock] = []

    def _say(ask: str, *, expect: int | None) -> tuple[tuple[ScriptBlock, ...], str]:
        response = chat_fn(
            model, prompt=ask, temperature=0.4, max_tokens=2000, timeout=TIMEOUT_S
        )
        raw = getattr(response, "text", "") or ""
        return parse_blocks(raw, expect=expect), raw

    def _call() -> tuple[str, str, str]:
        blocks, raw = _say(prompt, expect=BLOCK_COUNT)
        pacing: list = []
        unmapped: list = []

        for attempt in range(1, MAX_ATTEMPTS + 1):
            findings = [(b, check_narration(b.narration)) for b in blocks]
            pacing = [(b, f) for b, f in findings if not f.passed]
            problems = validate_script(story, blocks).problems

            # Two different failures wearing one name. The model citing a fact
            # that does not say what it claims is an integrity failure, and
            # asking politely for a nicer version of that is how a validator
            # becomes a formality — so those are terminal.
            terminal = [p for p in problems if p.kind in TERMINAL_KINDS]
            if terminal:
                return "reject", "\n".join(str(p) for p in terminal), raw

            # An unmapped number is different: usually the model stated a real
            # figure and simply did not declare it. Worth one ask, and the ask
            # cannot launder a fabrication — the repair still has to produce
            # evidence that appears verbatim in a real fact.
            unmapped = [p for p in problems if p.kind == "unmapped_number"]

            if not pacing and not unmapped:
                accepted.extend(blocks)
                note = f" after {attempt - 1} repair pass(es)" if attempt > 1 else ""
                return "pass", f"{len(blocks)} blocks, every claim traced to a fact{note}", raw

            if attempt == MAX_ATTEMPTS:
                break

            # Repair only the blocks that failed, and splice them back in.
            # Asking for the whole script again churns: on the live CS-1 run,
            # blocks that had passed came back rewritten and newly broken, so
            # each round fixed some lines and broke others and it never
            # converged. A block that already satisfies POL-5 is finished.
            failing = sorted({b.n for b, _ in pacing} | {p.block for p in unmapped})
            fixed, raw = _say(_repair_prompt(prompt, pacing, unmapped, failing), expect=None)

            # Splice only the blocks that were asked about. The reply is allowed
            # to contain more — models resend the whole script however firmly
            # they are told not to — but a block that already satisfies POL-5 is
            # finished, and accepting a fresh version of it is what made the
            # live run oscillate instead of converge.
            replacements = {b.n: b for b in fixed if b.n in failing}
            blocks = tuple(replacements.get(b.n, b) for b in blocks)

        outstanding = [f"block {b.n}: POL-5 — {f.message}" for b, f in pacing]
        outstanding += [str(p) for p in unmapped]
        return (
            "reject",
            " | ".join(outstanding)
            + f" (after {MAX_ATTEMPTS} attempts — surfacing rather than retrying further)",
            raw,
        )

    state, ledger, _ = judged(
        state, ledger,
        role="script", model=model, provider=PROVIDER, call=_call, prompt=prompt,
    )
    return state, ledger, tuple(accepted)
