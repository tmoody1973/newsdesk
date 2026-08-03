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

from newsdesk.blockprompt import HOUSE_KIT, BlockPrompt

# The ground, verbatim from the house style. Stated first because it is the one
# element every block shares and the one that drifted when it was left implicit
# (MOO-424: two scenes off one style key produced a blue ground and a tan one).
GROUND = (
    "A warm cream paper background with visible halftone dot texture and paper grain"
)

# Anchors the frame so the accent palette appears even in a sparse composition.
ANCHOR = "Flat deep navy and coral torn-paper shapes anchor the lower corners"

# SUPERSEDED 2026-07-28. This read:
#
#   MOTION = "Elements settle into place with small paper shifts; a slow push in.
#             No camera shake, no whip pans, no parallax"
#   AUDIO  = "Quiet room tone with paper rustle; one soft tape peel on entry."
#
# One constant, used on all six blocks. It was written to stop the collage
# swooping like a template, and it worked — it also produced six static wides and
# a video Tarik called bland, correctly.
#
# The craft says the opposite, and says it in the section titled "what separates
# a banger from postcards" (vox-motion-graphics/SKILL.md):
#
#   "A sequence of pretty, disconnected scenes reads as a museum slideshow."
#   "Fake-oner. Write every clip as one continuous FPV camera move that begins
#    and ends in full motion blur (dive, whip, flare, fall) — hard cuts between
#    blocks then read as one unbroken shot."
#   "An impact every ~3 seconds and at least one speed ramp per block. Alternate
#    extreme macro and wide; whiplash the scale."
#
# So motion and audio are now per block, not constants. The five story-engine
# elements below are that section, implemented.

# 1 · FAKE-ONER. Each block is one continuous move that starts and ends in motion
# blur, so six hard cuts read as one unbroken shot. Block 1 opens from black;
# every later block emerges from the blur the previous one ended in.
_ENTRIES = (
    "Open from black, already moving",
    "Emerge from the motion-blurred paper dust the previous shot ended in",
    "Emerge from a motion-blurred whip across torn card",
    "Emerge from a motion-blurred fall through paper layers",
    "Emerge from a motion-blurred flare off the ground plane",
    "Emerge from a motion-blurred dive between paper layers",
)
_EXITS = (
    "end fully motion-blurred mid-dive into the paper",
    "end fully motion-blurred mid-whip",
    "end fully motion-blurred mid-fall",
    "end fully motion-blurred mid-flare",
    "end fully motion-blurred mid-dive",
    "settle, for the first and only time, and hold",
)

# 2 · SCALE WHIPLASH. Alternate extreme macro and wide. Never the same framing
# twice running — six identical compositions is the defect this replaces.
#
# These six say "the ground" and never name a colour or a material. The ground
# IS named, once, in the sentence build_scene() opens with — and it comes from
# the kit. Naming cream card here put the house palette inside every diorama
# SCENE, three sentences before that same field ends "one burnt-orange paper
# element is the only colour anywhere in the frame". Same defect GROUND and
# ANCHOR had; it needed no per-kit array, only wording that refers back instead
# of re-deciding.
_SHOTS = (
    "EXTREME MACRO on one torn edge of the object, so close the paper fibres show",
    "WIDE, the whole object small in a big empty field of the ground",
    "LOW ANGLE looking steeply up the object so it towers over the frame",
    "OVERHEAD FLAT-LAY looking straight down, the object foreshortened against the ground",
    "MACRO DETAIL on the part of the object the change is happening to",
    "CRANE REVEAL rising and pulling back until the whole arrangement is legible at once",
)

# 3 · ONE IMPACT EVERY ~3 SECONDS, and one speed ramp per block.
_IMPACTS = (
    # A hard black ring, not "a hand-drawn marker circle": the marker is the
    # house's own annotation device and this world annotates with printers ink
    # and censor bars. Both styles can draw a black circle closing on an object.
    "a hard black circle SNAPS closed around it",
    "a torn paper shape SLAMS into frame and stops dead",
    "a stamp PUNCHES down and paper dust bursts",
    "a card layer RIPS away in one stroke",
    "a shape DROPS in and bounces once",
    "every loose element SNAPS into its final position at once",
)
_RAMPS = (
    "a violent speed-ramp pull-back",
    "a slow-motion beat that whips back to full speed",
    "an abrupt ramp into slow motion, then a snap back",
    "a speed-ramp push that overshoots and settles",
    "a slow-motion hold that accelerates hard out",
    "a final slow-motion settle",
)

# 4 · MOTIF PER BLOCK. The design's Art Direction step names these six and
# defaults them from the through-line (Newsdesk Screens.dc.html, 1g). They are
# what makes a block about THIS story rather than about the object alone.
_MOTIFS = (
    "the object alone in the frame, nothing else competing",
    "a flat stylised map beneath it, regions filling in one at a time",
    "an abstract bar chart of torn card growing beside it, unlabelled",
    "a ruled ledger of paper strips stacking and un-stacking behind it",
    "a crowd of small faceless paper cutouts arranged below it",
    "an archival paper frame closing around it like a mount",
)

# 5 · SOUND DESIGN, three to five concrete diegetic events per block. The old
# constant asked for room tone on every block, which is the audio equivalent of
# six static wides.
_SOUND = (
    "paper fibre crackle, one marker squeak, a soft tape peel",
    "a low paper whump, sliding card, one distant room tone swell",
    "three accelerating card rips, a stamp punch, dust settling",
    "stacking paper taps, one ruler snap, a page turn",
    "a soft crowd shuffle of paper, one collective flutter, a held breath of room tone",
    "one last stamp punch, paper dust settling, silence opening up",
)

# The through-line only works if the viewer recognises the SAME object each time.
# The first six-block run held the palette perfectly and lost the object: blocks
# 1, 2 and 6 rendered lattice masts while 4 and 5 rendered observation towers
# with decks. Palette was pinned by naming it; identity has to be pinned the
# same way rather than assumed to carry.
# The object is identical across blocks; the framing is not.
#
# Says "framing" rather than "the shot on it" because POL-3 rejected the latter:
# "shot on" is how a request for camera realism is usually phrased, and the gate
# was right to stop it. A rule that only fires on other people's wording is not
# a rule. The first version of
# this clamp ended "...same position in frame", which fixed the object and froze
# the camera with it — and freezing the camera is how six blocks became six
# identical wides. Hold the object. Free the shot.
IDENTITY = (
    "This is the identical object in every block of this story — same silhouette, "
    "same proportions, same materials, same colours. Only its state and the "
    "framing change between blocks. Do not redesign the object"
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
    # Optional per-object shape lock. See through-lines.yaml for why it exists:
    # the framing clause names the object, the silhouette clause makes sure only
    # one thing satisfies it.
    silhouette: str = ""
    # Optional countable escalation: {"noun": ..., "start": int, "end": int}.
    # Present when the change is a thing that can be counted; absent when it is
    # continuous (a fuse shortening, a balloon filling), which still gets the
    # percentage phrasing below.
    countable: dict | None = None
    # The kit's ground and corner accent. Defaulted to the house constants so
    # every existing caller builds a byte-identical scene, and overridable
    # because they are the two clauses that name a PALETTE: a diorama block
    # built with the house ground says "aged sepia newsprint" in its STYLE line
    # and "warm cream paper, navy and coral" three words later in its SCENE.
    # They live in the kit's own art-direction file rather than here for the
    # same reason `framing` does — this is craft, and the kit is where craft
    # lives.
    ground: str = GROUND
    anchor: str = ANCHOR

    @classmethod
    def from_kit(cls, entry: dict, doc: dict | None = None) -> ThroughLine:
        """One menu entry, plus the kit-wide `scene:` block it came from."""
        scene = (doc or {}).get("scene") or {}
        return cls(
            id=entry["id"],
            label=entry["label"],
            framing=_flatten(entry["framing"]),
            escalation=_flatten(entry.get("escalation", "")),
            lettering_risk=entry.get("lettering_risk", "low"),
            surface=_flatten(entry.get("surface", "")),
            silhouette=_flatten(entry.get("silhouette", "")),
            countable=entry.get("countable"),
            ground=_flatten(scene.get("ground", "")) or GROUND,
            anchor=_flatten(scene.get("anchor", "")) or ANCHOR,
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
    parts = [f"{through_line.ground}. {framing}"]

    if through_line.surface:
        # Positive description of what IS on the surface, spliced into the same
        # sentence rather than appended as a prohibition. POL-4's prompting rule.
        parts[0] += f", where {through_line.surface}"

    parts[0] += "."

    # Immediately after the object is introduced and before anything else — the
    # same placement rule scene-guidance.txt found for the surface clause. A
    # shape constraint that arrives after two other sentences is a shape
    # constraint the model has already resolved without.
    if through_line.silhouette:
        # Capitalised on splice rather than in the kit, so an editor writing a
        # silhouette does not have to think about where their clause lands in
        # the sentence. tests/test_scene.py enforces this and caught it.
        shape = through_line.silhouette
        parts.append(f"{shape[:1].upper()}{shape[1:]}.")

    parts.append(f"{IDENTITY}.")

    i = _index(block_n, blocks)
    parts.append(f"Shot scale for this block: {_SHOTS[i]}.")
    parts.append(f"Also in frame: {_MOTIFS[i]}.")

    if through_line.countable:
        parts.append(f"{_count(through_line.countable, block_n, blocks)}.")
    elif through_line.escalation:
        parts.append(f"{_stage(through_line.escalation, block_n, blocks)}.")

    # The fake-oner, in the scene rather than only in the motion field, because
    # the entry and exit are composition decisions before they are camera ones.
    parts.append(
        f"{_ENTRIES[i]}. One continuous move through the scene; partway through, "
        f"{_IMPACTS[i]}. The shot does not stop — {_EXITS[i]}."
    )

    parts.append(f"{through_line.anchor}.")
    return " ".join(parts)


def _index(block_n: int, blocks: int) -> int:
    """Position in the six-beat arrays, clamped for stories of another length."""
    if blocks == len(_SHOTS):
        return block_n - 1
    scaled = round((block_n - 1) / max(blocks - 1, 1) * (len(_SHOTS) - 1))
    return max(0, min(scaled, len(_SHOTS) - 1))


def build_motion(block_n: int, blocks: int = 6) -> str:
    """MOTION for one block. One continuous move, one speed ramp, never static."""
    i = _index(block_n, blocks)
    return (
        f"ONE continuous camera move for the whole clip, never a static shot, "
        f"with {_RAMPS[i]}. The move begins already in motion and ends still "
        f"moving so this clip cuts into the next as one unbroken shot. "
        f"Paper elements move as layers with real parallax"
    )


def build_audio(block_n: int, blocks: int = 6) -> str:
    """AUDIO for one block: three to five concrete diegetic events. No voice."""
    return f"Sound design: {_SOUND[_index(block_n, blocks)]}. No voice, no narration"


def _count(spec: dict, block_n: int, blocks: int) -> str:
    """The escalation as an exact remaining count, not as a proportion.

    Six blocks of "about sixty percent through that change" came back
    non-monotonic twice — block 6 with more rings than block 1. A model cannot
    render a proportion of an abstract change, but it can render eight things
    and it can render three. Interpolated linearly and rounded, so consecutive
    blocks differ by a whole unit and the direction is never ambiguous.
    """
    start, end = int(spec["start"]), int(spec["end"])
    noun = str(spec["noun"])
    span = (block_n - 1) / max(blocks - 1, 1)
    now = round(start + (end - start) * span)
    return (
        f"Draw EXACTLY {now} {noun} — count them, there must be {now} and no "
        f"more. There were {start} at the start of this story and there will be "
        f"{end} by the end; this block shows {now}"
    )


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


def build_block_prompt(
    through_line: ThroughLine,
    block_n: int,
    blocks: int = 6,
    *,
    kit: str = HOUSE_KIT,
    label: str | None = None,
) -> BlockPrompt:
    """The five-field document that reaches the gate, then the provider.

    `kit` picks the STYLE REFERENCE and the NEGATIVE line. It defaults to the
    house kit so nothing that never heard of kits changes, and the pipeline
    passes the story file's own kit so the gate checks the prompt that is
    actually paid for.

    `label` is this block's claims-validated letterpress word, if it has one
    — `BlockPrompt.build` does the actual splicing; passed straight through so
    the gate and the render path build from the one place (`pipeline.py`).
    """
    return BlockPrompt.build(
        block_n,
        scene=build_scene(through_line, block_n, blocks),
        motion=build_motion(block_n, blocks),
        audio=build_audio(block_n, blocks),
        kit=kit,
        label=label,
    )
