"""Social captions for a finished run, held to the same standard as the script.

The caption guide asks a caption to "lead with the surprising number" and to
carry a Sources section. Both are claims leaving the building, which is why
this module reuses claims.py rather than trusting prose: a caption that says a
number the facts do not support is the same failure as a block that does, on a
surface nobody was checking.

The Sources block is assembled, never generated. The guide wants sources
because they "add immense credibility" — which is exactly why a model cannot
be the one to write them.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, replace
from typing import Any, Callable

from newsdesk.claims import Claim, ScriptBlock, validate_block
from newsdesk.decisions import Ledger, judged
from newsdesk.facts import Story
from newsdesk.script import MODEL, PROVIDER, TIMEOUT_S, chat
from newsdesk.state import RunState

# Instagram was the platform the product owner asked for first, and it was
# missing from this tuple for the feature's whole first day. The caption count
# everywhere derives from this tuple — two variants per platform — so adding a
# platform is one edit here, not a hunt for hardcoded fours.
PLATFORMS = ("instagram", "linkedin", "youtube")

# Characters visible before the platform truncates. The hook has to land whole
# inside this or the surprising number is cut off mid-sentence, which is the one
# thing the guide says must not happen.
# Instagram folds the caption behind "more" at ~125 visible characters.
HOOK_LIMIT = {"instagram": 125, "linkedin": 125, "youtube": 150}

MIN_HASHTAGS = 3
MAX_HASHTAGS = 5

# YouTube only. The guide: "You must include #Shorts as one of these tags to
# signal proper categorisation to the algorithm."
REQUIRED_TAG = {"youtube": "#Shorts"}


# Shouting is a RUN of caps words, not a single one. The stories this product
# exists to tell are about call letters and agencies — WPBS, KUAC, KUOW, RIAA
# all appear as bare facts (grep -rhoE "\b[A-Z]{4,}\b" stories/*.yaml), and
# each is one token standing alone. "THIS IS URGENT" is shouting because it is
# a *phrase* in all caps; "KUOW" is a station. Requiring two or more
# consecutive all-caps words tells them apart without ever reading the story's
# facts, so this stays a pure function of the caption. Word length floor is 2,
# not 4, so a run like "IS URGENT" still counts — it is the run that matters,
# not the length of any one word in it.
_ALL_CAPS_RE = re.compile(r"\b[A-Z]{2,}\b(?:\s+[A-Z]{2,}\b)+")

# An exclamation *run* is consecutive marks ("!!", "!!!"), not two separate
# sentences that each end in one. The old `!.*!` with re.DOTALL matched a hook
# and a CTA each carrying a single "!" as if they were one shout spanning the
# whole caption — refusing legitimate prose at the cost of a paid repair round.
_EXCLAIM_RUN_RE = re.compile(r"!{2,}")
_EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF]"
)


@dataclass(frozen=True)
class Caption:
    """One option for one platform. Immutable; a run cannot edit its own caption."""

    platform: str
    variant: int
    hook: str
    body: str
    cta: str
    hashtags: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()
    claims: tuple[Claim, ...] = field(default_factory=tuple)

    @property
    def prose(self) -> str:
        """The claim-bearing text. Hashtags and sources are not prose and are
        not generated, so they are excluded from tracing."""
        return f"{self.hook}\n\n{self.body}\n\n{self.cta}"

    @property
    def text(self) -> str:
        parts = [self.prose]
        if self.sources:
            parts.append("Sources:\n" + "\n".join(f"- {s}" for s in self.sources))
        if self.hashtags:
            parts.append(" ".join(self.hashtags))
        return "\n\n".join(parts)


def sources_for(story: Story) -> tuple[str, ...]:
    """Every source in the story, deduped, order preserved.

    Copied verbatim. Nothing here is generated and nothing may be added later:
    a caption source that is not in this tuple is refused.
    """
    seen: list[str] = []
    for fact in story.facts:
        for source in fact.sources:
            if source.value not in seen:
                seen.append(source.value)
    return tuple(seen)


def caption_problems(c: Caption) -> tuple[str, ...]:
    """Deterministic checks. Run before any model output is trusted, and free."""
    problems: list[str] = []

    limit = HOOK_LIMIT.get(c.platform)
    if limit is None:
        problems.append(f"unknown platform '{c.platform}'")
    elif len(c.hook) > limit:
        problems.append(
            f"hook is {len(c.hook)} characters; {c.platform} truncates at {limit}"
        )

    if not MIN_HASHTAGS <= len(c.hashtags) <= MAX_HASHTAGS:
        problems.append(
            f"{len(c.hashtags)} hashtags; the guide asks for "
            f"{MIN_HASHTAGS}-{MAX_HASHTAGS}"
        )

    required = REQUIRED_TAG.get(c.platform)
    if required and required not in c.hashtags:
        problems.append(f"{c.platform} captions must carry {required}")

    prose = c.prose
    if _ALL_CAPS_RE.search(prose):
        problems.append("all-caps shouting; the guide forbids it")
    if _EXCLAIM_RUN_RE.search(prose):
        problems.append("exclamation runs; the guide forbids them")
    if _EMOJI_RE.search(prose):
        problems.append("emoji; the guide keeps them at zero for this aesthetic")

    return tuple(problems)


# --- generation, checked and refused like a script block ---------------------

# 3 -> 6 on 2026-08-03: three consecutive full-loop refusals on mapping drift,
# measured on two real stories — the same convergence-out-of-budget shape the
# script stage documented at its own 4 -> 6 -> 8 moves. Attempts are text-priced.
MAX_ATTEMPTS = 6

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


class CaptionError(ValueError):
    """The model did not return usable captions."""


def build_prompt(story: Story, *, through_line: str, problems: str = "") -> str:
    facts = "\n".join(f"{f.id}: {f.text}" for f in story.facts)
    repair = f"\n\nThe previous attempt was rejected:\n{problems}\n" if problems else ""
    return f"""Write social captions for a finished 60-second explainer.

STORY: {story.title}

FACTS — every claim you make must map to one of these by id:
{facts}

THROUGH-LINE OBJECT: {through_line}. The video carries this object through all
six scenes. You may reference it once as a metaphor.

Write SIX captions: two for instagram, two for linkedin, two for youtube.

RULES
- The hook leads with the single most surprising real number, and must fit
  {HOOK_LIMIT['instagram']} characters for instagram, {HOOK_LIMIT['linkedin']} for linkedin, {HOOK_LIMIT['youtube']} for youtube.
- Short punchy sentences. Documentary tone, warm but not promotional.
- Tease the turn without giving it away.
- {MIN_HASHTAGS}-{MAX_HASHTAGS} hashtags, niche and specific, as category labels.
  youtube captions must include "#Shorts".
- No emoji. No all-caps. No exclamation runs.
- Do NOT write source URLs. Sources are attached by the system.
- Every claim you make goes in "claims" with the fact id it comes from and the
  supporting text copied verbatim from that fact.
- Use the fact's own verbs for claim-bearing assertions. A synonym breaks the
  trace: if the fact says "found", the caption says "found", not "discovered".{repair}

Return JSON only:
{{"captions": [{{"platform": "linkedin", "variant": 1, "hook": "...",
  "body": "...", "cta": "...", "hashtags": ["#A"],
  "claims": [{{"spoken": "...", "fact_id": "F1", "evidence": "..."}}]}}]}}"""


def parse_captions(text: str) -> tuple[Caption, ...]:
    fenced = _FENCE_RE.search(text or "")
    raw = fenced.group(1) if fenced else (text or "")
    try:
        doc = json.loads(raw)
    except json.JSONDecodeError:
        # A reply that opened a ```json fence and never closed it (usually a
        # truncated reply) defeats _FENCE_RE, which needs both ends. Same
        # rescue script.py uses: slice from the first brace to the last —
        # honest truncation still fails, but a merely unclosed fence parses.
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end > start:
            try:
                doc = json.loads(raw[start : end + 1])
            except json.JSONDecodeError:
                raise CaptionError(
                    f"the model did not return JSON. First 200 characters: {raw[:200]!r}"
                ) from None
        else:
            raise CaptionError(
                f"the model did not return JSON. First 200 characters: {raw[:200]!r}"
            ) from None
    entries = doc.get("captions") or []
    expected = 2 * len(PLATFORMS)
    if len(entries) != expected:
        raise CaptionError(f"expected {expected} captions, got {len(entries)}")
    out: list[Caption] = []
    for e in entries:
        out.append(Caption(
            # `or` not a dict default: a model sending "" would otherwise pass
            # the default straight through. See HANDOFF dead assumption 5.
            platform=(e.get("platform") or "").strip().lower(),
            variant=int(e.get("variant") or 0),
            hook=(e.get("hook") or "").strip(),
            body=(e.get("body") or "").strip(),
            cta=(e.get("cta") or "").strip(),
            hashtags=tuple(t.strip() for t in (e.get("hashtags") or []) if t.strip()),
            sources=tuple(s.strip() for s in (e.get("sources") or []) if s.strip()),
            claims=tuple(
                Claim(spoken=(c.get("spoken") or "").strip(),
                      fact_id=(c.get("fact_id") or "").strip(),
                      evidence=(c.get("evidence") or "").strip())
                for c in (e.get("claims") or [])
            ),
        ))
    return tuple(out)


def _problems(story: Story, caps: tuple[Caption, ...]) -> tuple[str, ...]:
    """Deterministic checks, then the same tracing rule the script runs."""
    allowed = set(sources_for(story))
    found: list[str] = []
    for c in caps:
        found.extend(f"{c.platform}/{c.variant}: {p}" for p in caption_problems(c))
        for s in c.sources:
            if s not in allowed:
                found.append(
                    f"{c.platform}/{c.variant}: source {s!r} is not in the story. "
                    "Sources are copied from the facts, never written."
                )
        for problem in validate_block(
            story, ScriptBlock(n=c.variant, narration=c.prose, claims=c.claims)
        ):
            found.append(f"{c.platform}/{c.variant}: {problem.message}")
    return tuple(found)


def generate_captions(
    state: RunState,
    ledger: Ledger,
    story: Story,
    blocks: tuple[Any, ...] = (),
    *,
    through_line: str,
    chat_fn: Callable[..., Any] | None = None,
    model: str | None = None,
) -> tuple[RunState, Ledger, tuple[Caption, ...]]:
    """Two captions per platform, or none. Never captions with a warning attached."""
    chat_fn = chat_fn or chat
    model = model or MODEL
    attached = sources_for(story)
    accepted: tuple[Caption, ...] = ()
    problems = ""

    def _call() -> tuple[str, str, str]:
        nonlocal accepted, problems
        raw = ""
        for _ in range(MAX_ATTEMPTS):
            ask = build_prompt(story, through_line=through_line, problems=problems)
            response = chat_fn(model, prompt=ask, temperature=0.4,
                              max_tokens=6000, timeout=TIMEOUT_S)
            raw = getattr(response, "text", "") or ""
            caps = parse_captions(raw)
            found = _problems(story, caps)
            if not found:
                # Sources are attached here, never taken from the model. A
                # model that sent them anyway is caught by `_problems` above
                # and the whole run is refused — silently overwriting an
                # invented source would hide a model doing the one thing it
                # was told never to do.
                accepted = tuple(replace(c, sources=attached) for c in caps)
                return "pass", f"{len(accepted)} captions, every claim traced", raw
            problems = "\n".join(found)
        return "reject", problems, raw

    state, ledger, _ = judged(
        state, ledger, role="caption", model=model, provider=PROVIDER, call=_call
    )
    return state, ledger, accepted
