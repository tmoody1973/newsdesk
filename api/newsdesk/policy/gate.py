"""Wall 2 — the deterministic policy gate.

This module must never be able to reach a provider. That is not a convention;
`tests/test_structure.py` walks its import graph and fails the build if a
network-capable package appears anywhere in it.

That constraint is what turns "no paid call happens on a blocked prompt" from a
promise into a property. The whole CS-4 red-team battery runs offline against a
spend-counting fake and asserts a total of exactly $0 — and it could not do
otherwise, because there is nothing here to spend with.

Deterministic checks run first because they are free. The LLM half only ever
sees prompts that already passed here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from newsdesk.blockprompt import BlockPrompt, negative_line

POLICY_FILE = Path(__file__).resolve().parents[3] / "policy" / "policy.yaml"

# Narration pacing, calibrated against the actual voice on 2026-07-28 rather
# than inherited. Four takes on eleven_v3 / Marcus Louis:
#
#   22 words, 1 sentence  -> 8.96s   26 words, 1 sentence -> 8.88s
#   23 words, 1 sentence  -> 8.56s   22 words, 5 sentences -> 9.92s  (only one in window)
#
# Word count is a poor predictor — more words came back shorter, and the rate
# ranged 2.22-2.93 w/s. Sentence-end pauses, not words, fill the ten seconds.
# This inverts the imported vox guidance, which was calibrated on a slower
# voice and says to prefer one flowing sentence.
#
# So this check is a COARSE PRE-FLIGHT BOUND only. The enforcement is the
# measured take (ffprobe on the rendered file) — the ElevenLabs adapter returns
# asset.duration as None, so it cannot come from the manifest either.
MIN_WORDS, MAX_WORDS = 23, 27
MIN_SENTENCES, MAX_SENTENCES = 2, 3
MAX_TAKE_SECONDS = 10.5
WORDS_PER_SECOND = 2.6  # measured mean; spread is wide enough that this only catches extremes

# POL-3. Requests for camera realism, in any of the phrasings that mean it.
#
# The negative lookbehinds are load-bearing, not defensive. The house style
# tokens themselves contain "non-photorealistic, no live-action" — without
# these, the gate flags its own brand kit and blocks every legitimate block.
# Caught by the CS-2 control case on first run.
_NEGATED = r"(?<!non-)(?<!non )(?<!no )(?<!not )(?<!never )"
_PHOTOREAL = re.compile(
    _NEGATED + r"\b(photo-?realistic|photo-?real|live[- ]action|real footage|"
    r"actual footage|news footage|documentary footage|shot on|dslr|8k photo|"
    r"cinematic realism|looks? like real|indistinguishable from real)\b",
    re.IGNORECASE,
)

# POL-4. Quoted strings and explicit lettering requests inside SCENE.
_QUOTED = re.compile(r"[\"“”']([^\"“”']{2,40})[\"“”']")
_TEXT_REQUEST = re.compile(
    r"\b(text reading|words? reading|the words?|caption reading|headline reading|"
    r"sign (?:that )?(?:reads|saying)|letters? spelling|spelling out|written on)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Finding:
    """One rule result. Same shape whether it passed or failed, so callers
    handle one type and the audit gets a row either way."""

    rule_id: str
    name: str
    passed: bool
    message: str = ""

    def __str__(self) -> str:
        return f"{self.rule_id} · {self.name}" + (f": {self.message}" if self.message else "")


@dataclass(frozen=True)
class GateResult:
    findings: tuple[Finding, ...]

    @property
    def passed(self) -> bool:
        return all(f.passed for f in self.findings)

    def failures(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if not f.passed)

    def explain(self) -> str:
        """What the journalist sees on the blocked card — plain language, rule cited."""
        return "\n".join(str(f) for f in self.failures())


@lru_cache(maxsize=1)
def _policy() -> dict:
    return yaml.safe_load(POLICY_FILE.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _names() -> dict[str, str]:
    return {r["id"]: r["name"] for r in _policy()["rules"]}


@lru_cache(maxsize=1)
def _public_figures() -> tuple[str, ...]:
    """Role-and-title phrases that resolve to one identifiable living person.

    Deliberately shallow. An exhaustive name list is unmaintainable and would
    give false confidence; POL-1's semantic half (chat()) is what catches the
    unnamed-but-identifying descriptions this cannot. This layer exists to
    reject the obvious cases for free.
    """
    return (
        "the president", "president of the united states", "vice president",
        "the prime minister", "the pope", "the governor", "the mayor",
        "the senator", "the congressman", "the congresswoman",
        "the chief justice", "the speaker of the house", "the candidate",
    )


def estimate_take_seconds(narration: str) -> float:
    """Rough take length. Deliberately optimistic — the real duration is measured
    from the completed TTS job (POL-5's render-time half); this only catches
    lines that cannot possibly fit."""
    return len(narration.split()) / WORDS_PER_SECOND


def check(prompt: BlockPrompt, *, narration: str = "", fact_ids: tuple[str, ...] = ()) -> GateResult:
    """Evaluate one block against every deterministic rule.

    Returns findings for all rules, passed or failed, so the audit records what
    was checked rather than only what broke.
    """
    n = _names()
    findings: list[Finding] = []
    haystack = f"{prompt.style_reference} {prompt.scene} {prompt.motion}".lower()

    # POL-1 — obvious real-person likeness requests
    hits = [p for p in _public_figures() if p in haystack]
    findings.append(Finding(
        "POL-1", n["POL-1"], not hits,
        f"requests a real person's likeness ({hits[0]}). "
        f"Use an abstract silhouette or an empty podium instead." if hits else "",
    ))

    # POL-2 — the exclusion line is fixed
    findings.append(Finding(
        "POL-2", n["POL-2"], prompt.negative_is_intact,
        "the NEGATIVE line was modified; it is a policy constant and may only be "
        "extended, never edited or removed." if not prompt.negative_is_intact else "",
    ))

    # POL-3 — no fabricated news scenes
    m = _PHOTOREAL.search(haystack)
    findings.append(Finding(
        "POL-3", n["POL-3"], m is None,
        f"asks for camera realism (\"{m.group(0)}\"). Generated footage that could "
        f"be mistaken for a camera is the harm this rule exists to prevent."
        if m else "",
    ))

    # POL-4 — no unsourced text on screen
    quoted = [q for q in _QUOTED.findall(prompt.scene) if q.upper() not in fact_ids]
    requested = _TEXT_REQUEST.search(prompt.scene)
    text_problem = quoted or requested
    findings.append(Finding(
        "POL-4", n["POL-4"], not text_problem,
        (f"SCENE requests on-screen text ({'\"' + quoted[0] + '\"' if quoted else requested.group(0)}). "
         f"Map it to an entered fact, or express it as an abstract highlight bar or marker circle.")
        if text_problem else "",
    ))

    # POL-5 — narration fits its block (coarse bound; measured take is enforcement)
    if narration:
        findings.append(check_narration(narration))

    return GateResult(findings=tuple(findings))


def check_narration(narration: str) -> Finding:
    """POL-5 on one line, independent of any block prompt.

    Split out so script generation (MOO-419) rejects an over-long line before it
    is ever paired with a prompt, without either module carrying its own copy of
    the window. One policy number, one place.
    """
    words = len(narration.split())
    sentences = len([p for p in re.split(r"[.!?]+", narration) if p.strip()])
    est = estimate_take_seconds(narration)
    ok = MIN_WORDS <= words <= MAX_WORDS and MIN_SENTENCES <= sentences <= MAX_SENTENCES

    why = []
    if not MIN_WORDS <= words <= MAX_WORDS:
        why.append(f"{words} words (need {MIN_WORDS}-{MAX_WORDS})")
    if not MIN_SENTENCES <= sentences <= MAX_SENTENCES:
        why.append(
            f"{sentences} sentence{'s' if sentences != 1 else ''} "
            f"(need {MIN_SENTENCES}-{MAX_SENTENCES}) — sentence-end pauses are what "
            f"fill the ten-second window, so one long sentence runs short"
        )

    return Finding(
        "POL-5", _names()["POL-5"], ok,
        f"{'; '.join(why)}. Estimated ~{est:.1f}s." if not ok else "",
    )


def negative_constant() -> str:
    """Re-exported so callers need not reach into blockprompt for POL-2."""
    return negative_line()
