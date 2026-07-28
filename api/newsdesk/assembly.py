"""Assembly: audio leads, picture follows (MOO-428, P0-7, design spec §6.6).

The timing model lives in this half of the module as pure functions, and the
ffmpeg calls live in the other. That split is not tidiness — every rule in §6.6
exists to remove a *named* failure, and most of those failures are silent in a
render. A centred take, a fixed window, evenly spaced gaps: none of them look
like bugs when you watch the file, they just make it feel machine-made. Rules
you cannot see have to be rules you can test.

The corrected model, in one line each:

1. Silence is stripped before any timing decision — done upstream in
   `narration.py`, and the numbers this module reads are already trimmed.
2. Measure, never infer. `asset.duration` is `None`; the take length came from
   `ffprobe`.
3. Narration starts 0.4s *after* its cut. Landing on the cut means the shot is
   never actually seen.
4. Block length follows the take: `lead_in + take + tail`. Gaps are allowed to
   be uneven, and here they are required to be.
5. The clip serves the voice — trim it or hold its last frame. Never stretch.
6. Music is an arc, not a loop.
7. Subtitles: at most two lines, timed to the trimmed audio.

The four nevers — speed-compressing the voice, stretching the video, squeezing
audio to fill a window, centring a take — appear nowhere below. There is no
`atempo`, no `setpts`, and no block window to centre anything inside of. Three
of the tests in `tests/test_assembly.py` exist purely to notice if one comes back.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from newsdesk.state import Approval, RunState

# The six-beat formula, same order as `script.ROLES`. Imported as a constant
# rather than from `script` so assembly does not drag a provider SDK in behind it.
ROLES = ("cold open", "stakes", "evidence", "evidence", "turn", "kicker")

# Roughly the width Anton fills across a 9:16 frame at the kit's size before a
# line wraps. Cues are split on this rather than on a word count because a line
# of long words wraps at fewer of them.
SUBTITLE_LINE_CHARS = 30
MAX_SUBTITLE_LINES = 2


class AssemblyError(RuntimeError):
    """Raised when a run cannot be assembled, or must not be."""


@dataclass(frozen=True)
class Contract:
    """The published assembly contract, read from the brand kit.

    Every number an editor might want to change lives here rather than in a
    constant, because §6.6's whole correction was that the *previous* numbers
    were wrong and nobody could see them.
    """

    lead_in_s: float
    tail_range: tuple[float, float]
    tail_by_role: dict[str, float]
    second_evidence_offset: float = 0.0

    def tail_for(self, role: str, *, occurrence: int = 0) -> float:
        """The gap after a line of this role, clamped into the published range.

        `occurrence` distinguishes the formula's two consecutive `evidence`
        blocks. Without it they take the same tail, which puts two identical
        gaps into a piece that only has five of them.
        """
        base = self.tail_by_role.get(role)
        if base is None:
            raise AssemblyError(
                f"the brand kit's tail_by_role has no entry for {role!r} — "
                f"refusing to invent a gap length"
            )
        low, high = self.tail_range
        return min(max(base + self.second_evidence_offset * occurrence, low), high)


@dataclass(frozen=True)
class BlockTiming:
    """One block's place on the timeline. Derived from its take, never assigned."""

    n: int
    role: str
    start_s: float
    lead_in_s: float
    take_s: float
    tail_s: float

    @property
    def length_s(self) -> float:
        return round(self.lead_in_s + self.take_s + self.tail_s, 3)

    @property
    def narration_start_s(self) -> float:
        return round(self.start_s + self.lead_in_s, 3)

    @property
    def end_s(self) -> float:
        return round(self.start_s + self.length_s, 3)


@dataclass(frozen=True)
class Cue:
    """One subtitle, timed against the assembled timeline."""

    start_s: float
    end_s: float
    text: str


def assembly_contract(kit_voice: dict[str, Any]) -> Contract:
    """Read the contract out of the published `voice.json`."""
    raw = (kit_voice.get("delivery") or {}).get("assembly_contract")
    if not isinstance(raw, dict) or "lead_in_s" not in raw:
        raise AssemblyError(
            "brand kit voice.json has no delivery.assembly_contract — the timing "
            "numbers are published, not compiled in. See design spec §6.6."
        )
    tails = {k: v for k, v in (raw.get("tail_by_role") or {}).items()
             if not k.startswith("_")}
    if not tails:
        raise AssemblyError("the assembly contract carries no tail_by_role")
    low, high = raw["tail_gap_s"]
    return Contract(
        lead_in_s=float(raw["lead_in_s"]),
        tail_range=(float(low), float(high)),
        tail_by_role={k: float(v) for k, v in tails.items()},
        second_evidence_offset=float(
            (raw.get("tail_by_role") or {}).get("_second_evidence_offset", 0.0)
        ),
    )


def plan_timeline(
    takes: Sequence[float | None],
    contract: Contract,
    *,
    roles: Sequence[str] = ROLES,
) -> tuple[BlockTiming, ...]:
    """Lay the blocks end to end, each one as long as its own take needs.

    This is the whole of the corrected model. There is no window to fit a take
    into, so there is nothing to centre it in and nothing to compress it to
    reach. A block is as long as `0.4 + take + tail`, and the piece is as long
    as the six of them add up to.
    """
    seen: dict[str, int] = {}
    blocks: list[BlockTiming] = []
    cursor = 0.0

    for i, take in enumerate(takes):
        if take is None:
            raise AssemblyError(
                f"block {i + 1} has no measured take. Assembly derives every "
                f"length from the take, so a missing one cannot be defaulted — "
                f"it can only be re-voiced."
            )
        role = roles[i] if i < len(roles) else roles[-1]
        occurrence = seen.get(role, 0)
        seen[role] = occurrence + 1

        block = BlockTiming(
            n=i + 1,
            role=role,
            start_s=round(cursor, 3),
            lead_in_s=contract.lead_in_s,
            take_s=float(take),
            tail_s=contract.tail_for(role, occurrence=occurrence),
        )
        blocks.append(block)
        cursor = block.end_s

    return tuple(blocks)


def clip_action(clip_s: float, block_s: float) -> tuple[str, float]:
    """What to do to a clip so it covers its block. Three verbs, and no fourth.

    `trim` returns the length to cut to, `hold` the extra seconds of last frame
    to freeze. There is deliberately no verb for changing the clip's rate: the
    picture serves the voice, and stretching video to fit audio is one of §6.6's
    four nevers.
    """
    if abs(clip_s - block_s) < 0.001:
        return "fit", block_s
    if clip_s > block_s:
        return "trim", round(block_s, 3)
    return "hold", round(block_s - clip_s, 3)


def approved_or_raise(state: RunState) -> Approval:
    """Wall 3. The only door, and it is locked from this side.

    Assembly calls this before anything else, so "publish is unreachable without
    an approval" is a property of the code path rather than of a UI that could be
    bypassed by curling the API.
    """
    if state.approval is None:
        raise AssemblyError(
            f"run {state.run_id} has no approval record. Assembly is Wall 3 — "
            f"a video cannot be built, let alone published, until a named human "
            f"has approved it. Run `newsdesk approve --name \"...\"` first."
        )
    return state.approval


def _wrap(words: Sequence[str]) -> str:
    """Fold a cue into at most two lines at the kit's width."""
    lines: list[list[str]] = [[]]
    for word in words:
        candidate = " ".join([*lines[-1], word])
        if lines[-1] and len(candidate) > SUBTITLE_LINE_CHARS and len(lines) < MAX_SUBTITLE_LINES:
            lines.append([word])
        else:
            lines[-1].append(word)
    # Uppercased here because ASS carries no text-transform and the kit's style
    # is "Anton, uppercase" — the same face and case as the app's stamps, which
    # is the UI spec's continuity rule made literal.
    return "\\N".join(" ".join(line) for line in lines).upper()


def subtitle_cues(narration: str, *, start_s: float, take_s: float) -> tuple[Cue, ...]:
    """Split a line into cues and time them across the trimmed take.

    Timed against the trimmed audio and offset to where that audio actually
    begins — `start_s` is the narration start, 0.4s into the block, not the
    block's own start.

    Proportional by character count rather than by word timings, and that is a
    known approximation: the takes were rendered without `with_timestamps`, and
    trimming the silence would have shifted those timings anyway. Character count
    tracks speaking time closely enough at this length because the split points
    are sentence boundaries, where the narrator pauses regardless.
    """
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", narration.strip()) if s]
    if not sentences:
        return ()

    chunks: list[list[str]] = []
    for sentence in sentences:
        words = sentence.split()
        # A sentence wider than two lines becomes two cues rather than a wall.
        budget = SUBTITLE_LINE_CHARS * MAX_SUBTITLE_LINES
        current: list[str] = []
        for word in words:
            if current and len(" ".join([*current, word])) > budget:
                chunks.append(current)
                current = []
            current.append(word)
        if current:
            chunks.append(current)

    total = sum(len(" ".join(c)) for c in chunks) or 1
    cues: list[Cue] = []
    cursor = start_s
    for i, chunk in enumerate(chunks):
        share = len(" ".join(chunk)) / total
        # The last cue is pinned to the end of the take rather than accumulated
        # to it, so rounding cannot leave a caption hanging past the audio.
        end = start_s + take_s if i == len(chunks) - 1 else cursor + take_s * share
        cues.append(Cue(start_s=round(cursor, 3), end_s=round(end, 3), text=_wrap(chunk)))
        cursor = end

    return tuple(cues)


# --- the render half -------------------------------------------------------
#
# Everything above is arithmetic and is tested at $0. Everything below shells
# out to ffmpeg, and its correctness is settled by watching the file.

# The delivery frame. The clips come back 704x1248 from seedance; this upscales
# once, with lanczos, to the standard vertical size the subtitle style's PlayRes
# already assumes. Upscaling costs a little sharpness and buys a file that every
# social target accepts without re-encoding it themselves — which would cost more.
OUT_W, OUT_H = 1080, 1920
FPS = 30


def _ts(seconds: float) -> str:
    """ASS timestamp: h:mm:ss.cc"""
    cs = int(round(seconds * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def ass_document(kit_subtitle: str, cues: Sequence[Cue]) -> str:
    """The kit's header and styles, with this run's events written under them.

    Two things are stripped, for two different reasons.

    The kit's leading comment block goes because **ffmpeg's ASS demuxer rejects
    a file with anything before `[Script Info]`** — and the error it raises is
    `Unable to open <path>`, which names the filename and says nothing about the
    content. Measured 2026-07-28: the burn failed identically from the project
    directory and from `/tmp`, which is what ruled out a permissions problem and
    pointed at the file itself. The comments are for whoever edits the kit; they
    are not part of what ships to libass.

    The kit's single `Dialogue:` line goes because it is a rendering probe
    reading "ANTON RESOLVED", meant to be burned once and looked at. A probe that
    survives into a finished video is a caption nobody wrote.
    """
    body = kit_subtitle[kit_subtitle.index("[Script Info]"):] if (
        "[Script Info]" in kit_subtitle
    ) else kit_subtitle
    head, _, _ = body.partition("Dialogue:")
    events = "\n".join(
        f"Dialogue: 0,{_ts(c.start_s)},{_ts(c.end_s)},Default,,0,0,0,,{c.text}"
        for c in cues
    )
    return f"{head.rstrip()}\n{events}\n"


# Homebrew's core `ffmpeg` bottle does **not** build libass — it lists no libass
# dependency and its configure line carries neither `--enable-libass` nor
# `--enable-libfreetype`, so `subtitles` is not a filter it has. Discovered at
# burn time on 2026-07-28, after the font was already installed and resolving.
# `ffmpeg-full` is the same tap, is bottled for arm64, and is keg-only — so it
# installs alongside without touching the existing `ffmpeg` link.
#
# Resolved rather than hardcoded, and checked by capability rather than by name:
# a build either has the filter or it does not, and asking is cheaper than
# discovering it in a render.
_FFMPEG_CANDIDATES = (
    os.getenv("NEWSDESK_FFMPEG"),
    "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg",
    "/usr/local/opt/ffmpeg-full/bin/ffmpeg",
    "ffmpeg",
)


def has_subtitles_filter(binary: str) -> bool:
    """Whether this ffmpeg was built with libass."""
    proc = subprocess.run([binary, "-hide_banner", "-filters"],
                          capture_output=True, text=True)
    return any(line.split()[1:2] == ["subtitles"] for line in proc.stdout.splitlines())


def resolve_ffmpeg(*, needs_subtitles: bool = True) -> str:
    """The ffmpeg to shell out to, chosen by what it can actually do."""
    seen = []
    for candidate in _FFMPEG_CANDIDATES:
        if not candidate:
            continue
        path = shutil.which(candidate) or (candidate if Path(candidate).exists() else None)
        if path is None:
            continue
        seen.append(path)
        if not needs_subtitles or has_subtitles_filter(path):
            return path
    raise AssemblyError(
        "no ffmpeg on this machine has the `subtitles` filter, so captions would "
        "not burn — and Homebrew's core ffmpeg bottle is built without libass, so "
        "this is the common case rather than a broken install.\n"
        f"  tried: {', '.join(seen) or 'nothing'}\n"
        "  fix:   brew install ffmpeg-full   (bottled, keg-only, leaves `ffmpeg` alone)\n"
        "  or:    set NEWSDESK_FFMPEG to a build with libass"
    )


def _run(cmd: list[str], *, what: str) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise AssemblyError(f"ffmpeg failed while {what}:\n{proc.stderr.strip()[-1500:]}")


def probe_duration(path: Path) -> float:
    """Seconds, from ffprobe. Same rule as narration: measure, never infer."""
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True,
    )
    try:
        return round(float(proc.stdout.strip()), 3)
    except ValueError:
        raise AssemblyError(f"ffprobe could not measure {path.name}") from None


def _video_chain(index: int, clip_s: float, block: BlockTiming) -> str:
    """One clip, cut or held to cover its block. Never re-timed.

    `setpts=PTS-STARTPTS` resets the timestamp origin after a trim — it is not a
    rate change, and it is the only place PTS is touched anywhere in this module.
    """
    action, amount = clip_action(clip_s, block.length_s)
    if action == "trim":
        head = f"[{index}:v]trim=0:{amount:.3f},setpts=PTS-STARTPTS"
    elif action == "hold":
        head = f"[{index}:v]tpad=stop_mode=clone:stop_duration={amount:.3f}"
    else:
        head = f"[{index}:v]null"
    return (
        f"{head},scale={OUT_W}:{OUT_H}:flags=lanczos,setsar=1,fps={FPS}[v{index}]"
    )


def build_filtergraph(
    blocks: Sequence[BlockTiming], clip_seconds: Sequence[float], n_clips: int
) -> str:
    """The whole edit as one graph: picture cut to the voice, voice placed on the cut.

    Audio is placed by delay rather than by concatenating silence, so each take
    sits at exactly its measured narration start and nothing is padded to fit.
    `normalize=0` on the mix matters — the takes never overlap, so normalising
    would divide six non-overlapping tracks by six and quietly drop the voice
    18dB.
    """
    parts = [_video_chain(i, clip_seconds[i], blocks[i]) for i in range(n_clips)]
    parts.append(
        "".join(f"[v{i}]" for i in range(n_clips)) + f"concat=n={n_clips}:v=1:a=0[vcat]"
    )
    for i, block in enumerate(blocks):
        delay_ms = int(round(block.narration_start_s * 1000))
        parts.append(
            f"[{n_clips + i}:a]aresample=48000,adelay={delay_ms}:all=1[a{i}]"
        )
    parts.append(
        "".join(f"[a{i}]" for i in range(len(blocks)))
        + f"amix=inputs={len(blocks)}:normalize=0:duration=longest[aout]"
    )
    return ";".join(parts)


def render(
    blocks: Sequence[BlockTiming],
    clips: Sequence[Path],
    takes: Sequence[Path],
    *,
    ass_path: Path,
    out: Path,
    fonts_dir: Path | None = None,
    ffmpeg: str | None = None,
) -> Path:
    """Cut the picture to the voice and burn the captions. One pass, one file."""
    clip_seconds = [probe_duration(c) for c in clips]
    graph = build_filtergraph(blocks, clip_seconds, len(clips))

    # Three separate things bite here, and each one fails differently:
    #   - the filter parser splits options on ':' and reads '=' as key/value, so a
    #     bare path is taken for an option name ("No option name near ...")
    #   - quoting the value makes libass open a file whose name includes the
    #     quotes ("Unable to open ...")
    #   - the path is resolved by libass, not by the shell, so a relative one is
    #     resolved against something that is not the working directory
    # Absolute, named, escaped, unquoted.
    escaped = str(ass_path.resolve()).replace("\\", r"\\").replace(":", r"\:")
    burn = f"subtitles=filename={escaped}"
    if fonts_dir is not None:
        burn += f":fontsdir={str(Path(fonts_dir).resolve())}"

    cmd = [ffmpeg or resolve_ffmpeg(), "-y", "-loglevel", "error"]
    for path in [*clips, *takes]:
        cmd += ["-i", str(path)]
    cmd += [
        "-filter_complex", f"{graph};[vcat]{burn}[vout]",
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-profile:v", "high",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart",
        str(out),
    ]
    _run(cmd, what=f"assembling {len(blocks)} blocks")
    if not out.exists():
        raise AssemblyError("ffmpeg reported success but wrote no file")
    return out


def anton_is_resolvable() -> bool:
    """Whether libass will find the kit's typeface.

    ffmpeg does not embed a font and a missing face falls back **silently**, so
    this is checked before a render rather than discovered by watching one.
    """
    proc = subprocess.run(["fc-list"], capture_output=True, text=True)
    return "anton" in proc.stdout.lower()
