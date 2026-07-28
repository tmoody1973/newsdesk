#!/usr/bin/env python3
"""Six CS-1 takes, measured and landed in B2 (MOO-426, P0-5).

    uv run python scripts/run_cs1_narration.py
    uv run python scripts/run_cs1_narration.py --reuse       # skip the GMI script call
    uv run python scripts/run_cs1_narration.py --sabotage    # CS-5's TTS leg

Generates the CS-1 script, voices all six blocks on the published narrator,
strips the silence off each take, measures the trimmed file with ffprobe,
corrects anything outside the published window, and uploads what survives.

`--sabotage` hands ElevenLabs a revoked key and nothing else. The run must
complete on LMNT with no manual step, and the per-block report must name the
provider that actually spoke — a fallback nobody can see in the record is not a
fallback, it is a substitution.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))

from fixtures import cs1_story  # noqa: E402
from genblaze_elevenlabs import ElevenLabsTTSProvider  # noqa: E402
from genblaze_lmnt import LMNTProvider  # noqa: E402

from newsdesk.brandkit import load  # noqa: E402
from newsdesk.config import ConfigError, require  # noqa: E402
from newsdesk.decisions import Ledger  # noqa: E402
from newsdesk.narration import (  # noqa: E402
    narrate,
    speaker,
    store_take,
    take_window,
    voice_specs,
)
from newsdesk.pricing import register_all  # noqa: E402
from newsdesk.script import generate_script  # noqa: E402
from newsdesk.state import Attempt, Block, RunState  # noqa: E402

SCRIPT_CACHE = Path("out/cs1-script.json")

# The sabotage run writes to its own prefix. Sharing one would let a deliberately
# crippled run overwrite the takes the healthy run just produced, which is a
# quiet way to make the demo worse by proving the fallback works.
PREFIXES = {False: "cs1-narration", True: "cs1-narration-sabotage"}


def script_lines(reuse: bool) -> list[dict]:
    """The six lines, from cache if asked and available.

    Cached because iterating on narration should not keep paying for a script
    that already passed every claim check — and because a *different* script
    between two narration runs makes their durations incomparable.
    """
    if reuse and SCRIPT_CACHE.exists():
        return json.loads(SCRIPT_CACHE.read_text())["blocks"]

    require("GMI_API_KEY")
    story = cs1_story()
    _, ledger, blocks = generate_script(
        RunState(run_id="cs1-narration", story=story.title), Ledger(), story
    )
    if not blocks:
        raise SystemExit(f"script refused — {ledger.decisions[0].reason}")
    lines = [{"n": b.n, "role": b.role, "narration": b.narration} for b in blocks]
    SCRIPT_CACHE.parent.mkdir(parents=True, exist_ok=True)
    SCRIPT_CACHE.write_text(json.dumps({"blocks": lines}, indent=2))
    return lines


def main() -> int:
    sabotage = "--sabotage" in sys.argv
    try:
        require("ELEVENLABS_API_KEY", "LMNT_API_KEY", "B2_KEY_ID", "B2_APP_KEY")
    except ConfigError as exc:
        print(f"FAIL  {exc}")
        return 1

    kit = load()
    primary, fallback = voice_specs(kit.voice)
    window = take_window(kit.voice)
    lines = script_lines("--reuse" in sys.argv)

    elevenlabs = ElevenLabsTTSProvider(
        api_key="sk_revoked_for_cs5" if sabotage else None
    )
    lmnt = LMNTProvider()
    register_all(elevenlabs=elevenlabs, lmnt=lmnt)
    speak = speaker({"elevenlabs": elevenlabs, "lmnt": lmnt})

    print(f"narrator  {primary.voice_name} on {primary.model} "
          f"→ {fallback.voice_name} on {fallback.model}")
    print(f"window    {window[0]}-{window[1]}s")
    if sabotage:
        print("SABOTAGE  ElevenLabs key revoked — LMNT must carry the whole run")
    print()

    takes = [
        store_take(t, prefix=PREFIXES[sabotage])
        for t in asyncio.run(narrate(
            [(line["n"], line["narration"]) for line in lines],
            specs=[primary, fallback], window=window, speak=speak,
        ))
    ]

    state = RunState(
        run_id="cs1-narration",
        story=cs1_story().title,
        blocks=tuple(Block(n=line["n"], narration=line["narration"]) for line in lines),
    )

    total, failures, off_window = 0.0, 0, 0
    for take in sorted(takes, key=lambda t: t.n):
        total += take.cost_usd
        failures += 0 if take.status != "failed" else 1
        off_window += 1 if take.status == "review" else 0

        flag = "  FALLBACK" if take.used_fallback else ""
        print(f"block {take.n}  {take.status:<7} {take.provider or '—':<11}"
              f"${take.cost_usd:.4f}{flag}")
        if take.duration_s is not None:
            print(f"          raw {take.raw_duration_s:5.2f}s  trimmed {take.duration_s:5.2f}s"
                  f"  stripped {take.trimmed_s:4.2f}s  re-voices {take.revoices}")
        if take.revoices or take.status == "review":
            # Every attempt with its measured length. Without this the loop is
            # unfalsifiable: "two corrections, still short" cannot be told apart
            # from "two corrections, each one moved it, still not enough".
            trail = "  ".join(
                f"{a.get('duration_s', '—')}s/{a['status']}" for a in take.attempts
            )
            print(f"          attempts  {trail}")
        if take.note:
            print(f"          {take.note}")
        if take.uri:
            print(f"          {take.uri}")

        state = state.with_block(
            take.n,
            status="ready" if take.ok else ("failed" if take.status == "failed" else "voicing"),
            voice_uri=take.uri,
            voice_duration_s=take.duration_s,
            attempts=tuple(
                Attempt(n=i + 1, provider=a.get("provider", "?"), model=a.get("model", "?"),
                        status=str(a.get("status")), cost_usd=a.get("cost_usd"),
                        note=a.get("detail"))
                for i, a in enumerate(take.attempts)
            ),
        ).log(
            "narrate", f"block {take.n} voiced by {take.provider} at {take.duration_s}s",
            block=take.n, provider=take.provider, model=take.model,
            cost_usd=take.cost_usd,
        )

    runtime = sum(t.duration_s or 0.0 for t in takes)
    print(f"\n{len(takes) - failures}/{len(takes)} voiced · {off_window} outside window "
          f"· narration runtime {runtime:.1f}s · spend ${total:.4f}")
    print(f"state     b2://newsdesk-runs/{state.save()}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
