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
MODEL = os.getenv("NEWSDESK_SCRIPT_MODEL", "deepseek-ai/DeepSeek-V3")
PROVIDER = "gmicloud"

# The six-beat formula, imported from ~/.claude/skills/vox-motion-graphics via
# design spec §6.2 rather than invented here.
ROLES = ("cold open", "stakes", "evidence", "evidence", "turn", "kicker")

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


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
- Spell numbers out as they are spoken: "one point one billion dollars", not "$1.1B".
- Assert nothing that is not in the facts above. Do not compute new figures from
  them — a derived number is an unsourced number.
- For every quantity you state, emit a claim with:
    spoken   — the phrase exactly as it appears in your narration
    fact_id  — the fact it comes from
    evidence — the supporting text copied verbatim from that fact
- Claims are also welcome for non-numeric assertions. Every claim is checked.

Reply with JSON only, no commentary:
{{"blocks": [{{"n": 1, "role": "cold open", "narration": "...",
  "claims": [{{"spoken": "...", "fact_id": "F1", "evidence": "..."}}]}}]}}
"""


def parse_blocks(text: str) -> tuple[ScriptBlock, ...]:
    """Parse the model's reply into blocks. Tolerant of fences, strict about shape."""
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
    if len(raw) != BLOCK_COUNT:
        raise ScriptError(f"expected {BLOCK_COUNT} blocks, got {len(raw)}")

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

    def _call() -> tuple[str, str, str]:
        response = chat_fn(model, prompt=prompt, temperature=0.4, max_tokens=2000)
        raw = getattr(response, "text", "") or ""
        blocks = parse_blocks(raw)

        pacing = [
            f"block {b.n}: POL-5 — {finding.message}"
            for b, finding in ((b, check_narration(b.narration)) for b in blocks)
            if not finding.passed
        ]
        tracing = validate_script(story, blocks)

        if pacing or not tracing.passed:
            reasons = pacing + ([tracing.explain()] if not tracing.passed else [])
            return "reject", " | ".join(reasons), raw

        accepted.extend(blocks)
        return "pass", f"{len(blocks)} blocks, every claim traced to a fact", raw

    state, ledger, _ = judged(
        state, ledger,
        role="script", model=model, provider=PROVIDER, call=_call, prompt=prompt,
    )
    return state, ledger, tuple(accepted)
