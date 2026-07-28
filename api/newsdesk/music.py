"""The music bed, as an arc (MOO-428, design spec §6.6 point 6).

Lo-fi hip hop, instrumental, analog, keys — the house direction. It sits on the
same ground the pictures do: warm paper, tape saturation, a Rhodes rather than a
piano. It is also the right emotional register for this desk. A story about a
funding cut is loss, not threat, and lo-fi does not ask a viewer to feel anything
the facts have not earned.

**Why ElevenLabs Music specifically, and this belongs in the receipt rather than
in a preference file:** it is trained on licensed catalogue. A tool whose entire
argument is that generated media should carry provenance cannot score its own
video with a model that cannot say where its training came from. The bed is an
asset like any other and the manifest accounts for it like any other.

**The arc is the hard part, and it is why a track could not simply be chosen.**
§6.6: *music is an arc, not a loop* — one flat loop is what makes sixty seconds
feel like three, and lo-fi is loop-native, so this is the genre's specific
failure mode rather than a general caution. The answer is that the movement
boundaries are not invented: they are the **block boundaries the timeline
already computed**, so the bed changes exactly where the story changes and never
mid-sentence.

Four movements against the six-beat formula:

    open    block 1        keys and a light kit, stating the palette
    settle  blocks 2-3     kit present but restrained, under what CPB was
    trough  blocks 4-5     drums out, keys and vinyl noise, where the stations
                           and the tribal network land — the part of the story
                           that is people rather than policy
    lift    block 6        kit returns fuller, resolving under the kicker
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from newsdesk.assembly import BlockTiming

# Which blocks each movement covers, by 1-based block number. Keyed to the
# six-beat formula rather than to clock time, so a longer story keeps the shape.
MOVEMENTS: dict[str, tuple[int, ...]] = {
    "open": (1,),
    "settle": (2, 3),
    "trough": (4, 5),
    "lift": (6,),
}

MODEL = os.getenv("NEWSDESK_MUSIC_MODEL", "music_v2")

# Where the bed sits in the clear, in LUFS. The narration measures about
# -17.4 LUFS, so this puts the bed roughly 15dB under it before the sidechain
# pushes it further down under speech — the range a documentary bed lives in.
#
# A target rather than a fixed gain, because the fixed gain was wrong in a way
# that only measurement showed: the composed bed came back at **-14.3 LUFS**,
# louder than the voice it sits under. Any hand-picked multiplier would have
# been guessing at a number the file already knows.
BED_TARGET_LUFS = -32.0

# Fallback multiplier if loudness cannot be measured. Deliberately conservative:
# too quiet is a bed nobody notices, too loud is a bed that buries the story.
BED_GAIN = 0.13

GLOBAL_POSITIVE = [
    "lo-fi hip hop",
    "instrumental",
    "analog warmth, tape saturation, subtle vinyl crackle",
    "Rhodes and felt-piano keys",
    "unhurried boom-bap drums, brushed and soft",
    "warm upright bass",
    "documentary underscore, restrained, never sentimental",
]

GLOBAL_NEGATIVE = [
    "vocals",
    "vocal chops",
    "lyrics",
    "spoken word",
    "bright supersaw synths",
    "EDM builds and drops",
    "orchestral swells",
    "trailer percussion",
    "anything that competes with a speaking voice",
]

_LOCAL: dict[str, tuple[list[str], list[str]]] = {
    "open": (
        ["keys state the theme", "light brushed kit enters", "warm and open"],
        ["busy percussion"],
    ),
    "settle": (
        ["steady restrained groove", "bass holds the floor", "keys recede"],
        ["fills", "melodic movement that pulls focus"],
    ),
    "trough": (
        ["drums drop out", "keys and vinyl noise only", "sparse, spacious, quiet"],
        ["drums", "percussion", "bass drive"],
    ),
    "lift": (
        ["kit returns fuller", "keys resolve", "warm close, no crescendo"],
        ["triumphant", "crescendo", "big finish"],
    ),
}


@dataclass(frozen=True)
class Span:
    """One movement's place on the timeline, in whole milliseconds."""

    name: str
    first_block: int
    duration_ms: int


def movement_spans(timeline: Sequence[BlockTiming]) -> tuple[Span, ...]:
    """Cut the piece into movements on block boundaries.

    Rounded to whole milliseconds and reconciled at the end, so the sections sum
    to exactly the runtime rather than to within a rounding error — a bed that
    runs 40ms short leaves the last frame silent, which is audible and reads as
    a mistake rather than as an ending.
    """
    by_n = {b.n: b for b in timeline}
    total_ms = round(timeline[-1].end_s * 1000)

    spans: list[Span] = []
    for name, blocks in MOVEMENTS.items():
        present = [by_n[n] for n in blocks if n in by_n]
        if not present:
            continue
        start_ms = round(present[0].start_s * 1000)
        end_ms = round(present[-1].end_s * 1000)
        spans.append(Span(name=name, first_block=present[0].n,
                          duration_ms=end_ms - start_ms))

    drift = total_ms - sum(s.duration_ms for s in spans)
    if drift and spans:
        last = spans[-1]
        spans[-1] = Span(last.name, last.first_block, last.duration_ms + drift)
    return tuple(spans)


def build_plan(timeline: Sequence[BlockTiming]) -> Any:
    """The composition plan: one chunk per movement, no lyrics anywhere.

    **The two plan shapes are not interchangeable, and the API only says so at
    the wire.** `music_v1` takes a `MusicPrompt` — global styles plus
    `sections[SongSection]`. `music_v2` takes a `CompositionPlan` —
    `chunks[GenerationChunkInput]`, where styles are per chunk and there is no
    global layer. Handing v2 the v1 shape returns
    `Invalid type of composition_plan used for model music_v2`, which names the
    parameter and not the mismatch. So the house styles are merged into every
    chunk here rather than declared once.

    `text` is empty on every chunk, which is what makes this instrumental
    structurally: there is nothing to sing. `force_instrumental` cannot help —
    the API accepts it only alongside a bare `prompt`, never with a plan.

    `context_adherence="high"` is what keeps four movements sounding like one
    piece rather than four loops laid end to end, which is the whole of §6.6's
    arc requirement and the specific failure mode of this genre.
    """
    from elevenlabs.types.composition_plan import CompositionPlan
    from elevenlabs.types.generation_chunk_input import GenerationChunkInput

    return CompositionPlan(
        chunks=[
            GenerationChunkInput(
                text="",
                duration_ms=span.duration_ms,
                positive_styles=[*GLOBAL_POSITIVE, *_LOCAL[span.name][0]],
                negative_styles=[*GLOBAL_NEGATIVE, *_LOCAL[span.name][1]],
                context_adherence="high",
            )
            for span in movement_spans(timeline)
        ],
    )


def measure_lufs(path: Path, *, ffmpeg: str | None = None) -> float | None:
    """Integrated loudness of a file, from ebur128. `None` if it cannot be read."""
    import re
    import subprocess

    from newsdesk.assembly import resolve_ffmpeg

    binary = ffmpeg or resolve_ffmpeg(needs_subtitles=False)
    proc = subprocess.run(
        [binary, "-i", str(path), "-af", "ebur128=framelog=quiet", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    match = re.search(r"I:\s*(-?\d+(?:\.\d+)?)\s*LUFS", proc.stderr)
    return float(match.group(1)) if match else None


def gain_for(measured_lufs: float | None, *, target: float = BED_TARGET_LUFS) -> float:
    """Linear gain that moves a measured bed to the target level.

    A static gain, not `loudnorm`: normalising would compress the loudness range
    and flatten the arc into the loop §6.6 forbids. The trough is supposed to be
    quieter than the lift — that difference IS the arc, and a normaliser would
    helpfully remove it.
    """
    if measured_lufs is None:
        return BED_GAIN
    return round(10 ** ((target - measured_lufs) / 20), 4)


def compose(
    timeline: Sequence[BlockTiming],
    out: Path,
    *,
    client: Any | None = None,
    model: str = MODEL,
) -> Path:
    """Generate the bed and write it to `out`.

    `force_instrumental` is NOT passed, and that is the API's rule rather than a
    choice: it is only accepted alongside a bare `prompt`, and a plan carries the
    same guarantee structurally — every section has `lines=[]`, so there is
    nothing to sing, and "vocals" sits in the global negatives besides.

    `sign_with_c_2_pa` is on. C2PA is a documented Future Consideration for the
    product's own output (PRD P2-1) and is not built here — but it is free on
    this asset, and a provenance tool declining a provenance signature that was
    offered to it would be an odd thing to explain.
    """
    if client is None:
        from elevenlabs.client import ElevenLabs

        client = ElevenLabs()

    audio = client.music.compose(
        composition_plan=build_plan(timeline),
        model_id=model,
        sign_with_c_2_pa=True,
        output_format="mp3_44100_128",
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(b"".join(audio))
    return out
