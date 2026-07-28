#!/usr/bin/env python3
"""Does the v3 pause tag lengthen a take, or does the narrator read it out? (MOO-426)

    uv run python scripts/spike_pause_tag.py

Three renders of one line on `eleven_v3` — neutral, `[pause]`, `[long pause]` —
each trimmed and measured. Roughly $0.10.

The whole correction ladder rests on this. ElevenLabs documents SSML `<break>`
on every model *except* v3, and audio tags on v3 instead, so the lever we can
actually reach is `[short pause]` / `[pause]` / `[long pause]`.

MEASURED 2026-07-28, Marcus Louis on eleven_v3, 22 words across 3 sentences —
so two internal boundaries:

    variant      trimmed   vs neutral   internal silence (silencedetect -35dB)
    neutral       8.71s      +0.00s     0.57s + 0.40s = 0.97s
    [pause]       9.44s      +0.73s     1.29s + 0.67s = 1.97s
    [long pause] 11.20s      +2.49s     1.61s + 1.80s = 3.40s

**The tags are interpreted, not spoken**, and the silence measurement is what
proves it rather than the duration. Duration alone cannot tell the two apart —
a narrator reading "long pause" out loud also makes the take longer. But the
*added* time is silence: the growth in detected silence (+1.00s, +2.43s)
accounts for the growth in duration (+0.73s, +2.49s). Speech added by reading
the tag aloud would have moved those two numbers in opposite directions.

Word-level alignment is NOT a valid check here, and this was tried first: the
ElevenLabs timestamps endpoint aligns against the *input characters*, so the
tag appears in the returned "words" whether it was voiced or not.

Calibration, per internal boundary: `[pause]` ≈ +0.5s, `[long pause]` ≈ +1.2s.
Note also that a neutral read already pauses ~0.4-0.6s at each sentence end,
which is the mechanism voice.json measured when the only take that landed in
window was the choppy one.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from genblaze_elevenlabs import ElevenLabsTTSProvider

from newsdesk.brandkit import load
from newsdesk.config import ConfigError, require
from newsdesk.narration import (
    classify,
    paced,
    probe_duration,
    speaker,
    strip_silence,
    take_window,
    voice_specs,
)
from newsdesk.pricing import register_all

# Deliberately not from a fixture: the point is pacing behaviour, and a line the
# script model has never seen cannot have been tuned to pass.
LINE = (
    "Three hundred thousand households lost their water subsidy in a single "
    "budget cycle. Nobody announced it. The line item simply stopped appearing."
)

OUT = Path("out/spike-pause")


def main() -> int:
    try:
        require("ELEVENLABS_API_KEY", "B2_KEY_ID", "B2_APP_KEY")
    except ConfigError as exc:
        print(f"FAIL  {exc}")
        return 1

    kit = load()
    primary, _ = voice_specs(kit.voice)
    window = take_window(kit.voice)

    provider = ElevenLabsTTSProvider()
    register_all(elevenlabs=provider)
    speak = speaker({"elevenlabs": provider})

    OUT.mkdir(parents=True, exist_ok=True)
    print(f"voice   {primary.voice_name} ({primary.voice_id}) on {primary.model}")
    print(f"window  {window[0]}-{window[1]}s")
    print(f"line    {len(LINE.split())} words, {LINE.count('.')} sentences\n")

    variants = {
        "neutral": LINE,
        "pause": paced(LINE, "[pause]"),
        "long-pause": paced(LINE, "[long pause]"),
    }

    async def run() -> None:
        baseline = None
        for name, text in variants.items():
            rendered, cost = await speak(primary, text)
            keep = OUT / f"{name}.mp3"
            keep.write_bytes(rendered.read_bytes())
            raw = probe_duration(keep)
            trimmed = strip_silence(keep, OUT / f"{name}-trimmed.mp3")
            measured = probe_duration(trimmed)
            baseline = measured if baseline is None else baseline
            print(
                f"{name:<12} raw {raw:5.2f}s   trimmed {measured:5.2f}s   "
                f"stripped {raw - measured:4.2f}s   {classify(measured, window):<5} "
                f"  {measured - baseline:+5.2f}s vs neutral   ${cost:.4f}"
            )

    asyncio.run(run())
    print(f"\nFiles in {OUT}/ — LISTEN to them. A tag that lengthens the take by")
    print("being spoken aloud measures exactly like one that lengthens it correctly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
