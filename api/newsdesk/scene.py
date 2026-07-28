"""SCENE construction — the journalist picks a menu item, never writes framing.

A block's SCENE is assembled from three things the journalist never sees:
the house ground, the through-line's `framing` clause, and this block's position
in the escalation. That boundary is the point. `brand-kit/through-lines.yaml`
says it plainly — nobody using this tool should have to learn why a tower renders
as a paper cutout rather than a photograph.

Deterministic on purpose. This could have been another `chat()` call, but the
craft is already written down and settled; generating it would re-open every
question `scene-guidance.txt` closed, one render at a time.

Pure module: no provider access, no network. Same discipline as `claims.py`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from newsdesk.blockprompt import BlockPrompt

# The ground, verbatim from the house style. Stated first because it is the one
# element every block shares and the one that drifted when it was left implicit
# (MOO-424: two scenes off one style key produced a blue ground and a tan one).
GROUND = (
    "A warm cream paper background with visible halftone dot texture and paper grain"
)

# Anchors the frame so the accent palette appears even in a sparse composition.
ANCHOR = "Flat deep navy and coral torn-paper shapes anchor the lower corners"

# Motion is deliberately small. Collage that swoops reads as a template; collage
# that shifts by a few degrees reads as someone moving paper on a table.
MOTION = (
    "Elements settle into place with small paper shifts; a slow push in. "
    "No camera shake, no whip pans, no parallax"
)

AUDIO = "Quiet room tone with paper rustle; one soft tape peel on entry. No voice"

# The through-line only works if the viewer recognises the SAME object each time.
# The first six-block run held the palette perfectly and lost the object: blocks
# 1, 2 and 6 rendered lattice masts while 4 and 5 rendered observation towers
# with decks. Palette was pinned by naming it; identity has to be pinned the
# same way rather than assumed to carry.
IDENTITY = (
    "This is the identical object in every block of this story — same silhouette, "
    "same proportions, same materials, same position in frame. Only its state "
    "changes between blocks. Do not redesign it"
)


@dataclass(frozen=True)
class ThroughLine:
    """One art-direction menu option, as loaded from the brand kit."""

    id: str
    label: str
    framing: str
    escalation: str
    lettering_risk: str = "low"
    surface: str = ""

    @classmethod
    def from_kit(cls, entry: dict) -> ThroughLine:
        return cls(
            id=entry["id"],
            label=entry["label"],
            framing=_flatten(entry["framing"]),
            escalation=_flatten(entry.get("escalation", "")),
            lettering_risk=entry.get("lettering_risk", "low"),
            surface=_flatten(entry.get("surface", "")),
        )


def _flatten(text: str) -> str:
    """YAML folded scalars arrive with newlines; a prompt wants one line."""
    return re.sub(r"\s+", " ", (text or "").strip()).rstrip(".")


def build_scene(through_line: ThroughLine, block_n: int, blocks: int = 6) -> str:
    """The SCENE field for one block.

    Order matters and is not cosmetic. `scene-guidance.txt` records that the
    surface description has to arrive in the same sentence that introduces the
    object — naming blankness afterwards, as a separate exclusion, is what
    produced legible numerals on a radio dial three times out of four.
    """
    framing = through_line.framing[:1].upper() + through_line.framing[1:]
    parts = [f"{GROUND}. {framing}"]

    if through_line.surface:
        # Positive description of what IS on the surface, spliced into the same
        # sentence rather than appended as a prohibition. POL-4's prompting rule.
        parts[0] += f", where {through_line.surface}"

    parts[0] += "."

    parts.append(f"{IDENTITY}.")

    if through_line.escalation:
        parts.append(f"{_stage(through_line.escalation, block_n, blocks)}.")

    parts.append(f"{ANCHOR}.")
    return " ".join(parts)


def _stage(escalation: str, block_n: int, blocks: int) -> str:
    """Where the through-line has got to by this block.

    The menu describes the escalation as a process ("rings contract block by
    block"); the prompt needs its state now, as a quantity.

    The first version used three coarse buckets across six blocks, on the theory
    that a model cannot render "the fourth of six increments". The six-block run
    showed the real cost of that: the change did not read monotonically — block 2
    looked FULLER than block 1 — because two adjacent blocks were handed the
    identical description and the model was free to interpolate either way. A
    percentage is coarse enough to be renderable and monotonic enough to be
    legible, which the bucket was not.
    """
    percent = round(100 * (block_n - 1) / max(blocks - 1, 1))
    if block_n <= 1:
        return (
            f"The progression has not started. {escalation.capitalize()} — "
            f"show the object complete and unchanged, zero percent through that change"
        )
    if block_n >= blocks:
        return (
            f"{escalation.capitalize()} — this is the final block and the change is "
            f"one hundred percent complete, at its furthest extent"
        )
    return (
        f"{escalation.capitalize()} — this is block {block_n} of {blocks} and the "
        f"change is about {percent} percent complete, visibly further along than "
        f"the previous block and not yet finished"
    )


def build_block_prompt(through_line: ThroughLine, block_n: int, blocks: int = 6) -> BlockPrompt:
    """The five-field document that reaches the gate, then the provider."""
    return BlockPrompt.build(
        block_n,
        scene=build_scene(through_line, block_n, blocks),
        motion=MOTION,
        audio=AUDIO,
    )
