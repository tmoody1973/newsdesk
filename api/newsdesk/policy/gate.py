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

def _find_policy_file(start: Path | None = None) -> Path:
    """Walk up from this module until `policy/policy.yaml` turns up.

    This was `parents[3]`, which is right in the repo — `api/newsdesk/policy/`
    is three levels under the root — and wrong in the container, where
    `newsdesk/` sits directly under `/app` and the same expression resolved to
    `/policy/policy.yaml`. The gate then refused every block on the deployed
    worker with "checker unavailable ... blocked rather than assumed safe".

    That refusal was correct and is the reason this is a path bug rather than an
    incident: fail-closed meant a missing rulebook cost $0 instead of shipping
    six ungated prompts. But a rule that cannot be read is not a rule, so the
    lookup must not depend on how deep the package happens to sit.

    Searching upward is layout-independent and still finds exactly one file —
    there is one `policy/policy.yaml` and it is the one the web app publishes.
    """
    here = (start or Path(__file__)).resolve()
    for parent in here.parents:
        candidate = parent / "policy" / "policy.yaml"
        if candidate.is_file():
            return candidate
    # Nothing found: hand back the repo-layout path so the error names the
    # place a developer expects it, and let the caller fail closed.
    return here.parents[3] / "policy" / "policy.yaml"


POLICY_FILE = _find_policy_file()

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

# POL-4's element budget, for the one case where lettering is permitted at all:
# a question-on-prop that maps to an entered fact. Past three elements, or four
# words in any one of them, models stop rendering text and start approximating
# it — duplicating an element, stacking near-identical lines, garbling the
# longest. Numbers from the Vox-Style Explainer Prompt Pack, and they agree with
# through-lines.yaml's independent advice to keep an on-prop question to two or
# three words. See policy.yaml POL-4 element_budget_why.
MAX_TEXT_ELEMENTS = 3
MAX_WORDS_PER_ELEMENT = 4

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


def check(
    prompt: BlockPrompt,
    *,
    narration: str = "",
    fact_ids: tuple[str, ...] = (),
    labels: tuple[str, ...] = (),
) -> GateResult:
    """Evaluate one block against every deterministic rule.

    Returns findings for all rules, passed or failed, so the audit records what
    was checked rather than only what broke.

    `labels` sources POL-4 the same way `fact_ids` does, for the diorama
    style's one legal kind of on-prop text: a letterpress word already
    validated by claims.py against an entered fact, before it ever reached
    this prompt. The gate does not re-derive that — there is no fact list
    here to check it against, by design (this module must never import
    claims.py; see the module docstring on why nothing here reaches a
    provider). It accepts a label ONLY because the caller attests it was
    claims-validated. A caller that passes an unvalidated string as a label is
    the one thing this function cannot defend against; that is claims.py's job,
    upstream, once, rather than this file's job on every call. What this
    function DOES defend, as a second line of defence: an attested label that
    never actually shows up as quoted SCENE text — outside `_QUOTED`'s 2-40
    character window, or carrying a quote mark of its own — refuses POL-4
    rather than passing having verified nothing. That closes the gap for any
    future caller that skips claims.py's own bound (`LABEL_MAX_CHARS`) and
    hands this a label the regex cannot see.
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

    # POL-4 — no unsourced text on screen, and a budget on the sourced kind
    all_quoted = _QUOTED.findall(prompt.scene)
    quoted_upper = {q.upper() for q in all_quoted}
    labels_upper = {label.upper() for label in labels}
    unsourced = [
        q for q in all_quoted if q.upper() not in fact_ids and q.upper() not in labels_upper
    ]
    requested = _TEXT_REQUEST.search(prompt.scene)
    # Defence-in-depth against a caller that skipped claims.py's own length and
    # quote-character bound (see LABEL_MAX_CHARS there): `_QUOTED` only
    # captures a quoted span of 2-40 characters, so an attested label outside
    # that window — or containing a quote mark of its own — never shows up in
    # `all_quoted` at all. Left unchecked that reads as "nothing to inspect"
    # and POL-4 passes having verified nothing about text it was told exists.
    # Refuse-never-warn: a label the gate cannot see is refused, not waved
    # through on the caller's word.
    unseen_labels = [label for label in labels if label.upper() not in quoted_upper]

    # Checked in severity order: an unsourced word is a policy violation, while
    # too many sourced ones is a craft bound. Reporting the bound first would
    # bury the violation under a quibble about counting.
    if unsourced or requested:
        problem = (
            f"SCENE requests on-screen text "
            f"({'\"' + unsourced[0] + '\"' if unsourced else requested.group(0)}). "
            f"Map it to an entered fact, or express it as an abstract highlight bar "
            f"or marker circle."
        )
    elif unseen_labels:
        problem = (
            f"label {unseen_labels[0]!r} was attested but is not visible to POL-4 as "
            f"quoted SCENE text — it may be too short, too long, or itself contain a "
            f"quote character. A label the gate cannot see is a label it cannot bind."
        )
    elif len(all_quoted) > MAX_TEXT_ELEMENTS:
        problem = (
            f"{len(all_quoted)} text elements in one scene (limit {MAX_TEXT_ELEMENTS}). "
            f"Past that a model stops rendering text and starts approximating it — "
            f"duplicating an element or garbling the longest. Cut to the one that "
            f"carries the idea."
        )
    elif any(len(q.split()) > MAX_WORDS_PER_ELEMENT for q in all_quoted):
        longest = max(all_quoted, key=lambda q: len(q.split()))
        problem = (
            f"\"{longest}\" is {len(longest.split())} words on screen "
            f"(limit {MAX_WORDS_PER_ELEMENT}). Longer strings come back garbled, and a "
            f"garbled word reads as a misquote of a real source rather than as an "
            f"artefact. Shorten it or move it to narration."
        )
    else:
        problem = ""

    findings.append(Finding("POL-4", n["POL-4"], not problem, problem))

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
