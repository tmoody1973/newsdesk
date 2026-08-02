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

import re
from dataclasses import dataclass, field

from newsdesk.claims import Claim
from newsdesk.facts import Story

PLATFORMS = ("linkedin", "youtube")

# Characters visible before the platform truncates. The hook has to land whole
# inside this or the surprising number is cut off mid-sentence, which is the one
# thing the guide says must not happen.
HOOK_LIMIT = {"linkedin": 125, "youtube": 150}

MIN_HASHTAGS = 3
MAX_HASHTAGS = 5

# YouTube only. The guide: "You must include #Shorts as one of these tags to
# signal proper categorisation to the algorithm."
REQUIRED_TAG = {"youtube": "#Shorts"}

_ALL_CAPS_RE = re.compile(r"\b[A-Z]{4,}\b")
_EXCLAIM_RUN_RE = re.compile(r"!\s*!|!.*!", re.DOTALL)
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
