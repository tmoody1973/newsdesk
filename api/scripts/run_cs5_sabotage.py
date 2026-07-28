#!/usr/bin/env python3
"""CS-5 — resilience under provider failure (MOO-424).

    uv run python scripts/run_cs5_sabotage.py [--sabotage 3,4] [--doomed 5]

Sabotages the primary video model on the named blocks so they must complete on
the fallback, and proves the manifest records which provider actually ran.

`--doomed` additionally poisons the *whole* chain for one block, to confirm the
run reports FAILED rather than quietly shipping five clips and a gap.

Sabotage method is the case study's: an invalid model ID. Note that this does
NOT exercise genblaze's own `fallback_models` — its classifier only reaches
MODEL_ERROR for messages saying "not found" or "not available", and GMI says
"model X does not exist". That was measured, and it is why `blocks.run_block`
walks the chain itself. Running this against the SDK's chain alone would have
looked like a pass while never attempting a fallback.

~$0.88 on a six-block run with two sabotaged: four blocks at $0.061 on seedance,
two at $0.319 on the Kling fallback.
"""

from __future__ import annotations

import asyncio
import sys

from genblaze_gmicloud import GMICloudImageProvider, GMICloudVideoProvider

from newsdesk.blocks import (
    VIDEO_FALLBACKS,
    VIDEO_MODEL,
    register_seedance_ratio,
    run_block,
    sink,
)
from newsdesk.brandkit import load
from newsdesk.config import ConfigError, require
from newsdesk.policy.gate import check
from newsdesk.pricing import register_all
from newsdesk.scene import ThroughLine, build_block_prompt

BLOCKS = 6
# A REAL catalogued slug that passes preflight and then 401s on the wire. That
# is CS-5's scenario — "revoked key on Seedance" — a provider dying mid-run.
#
# The obvious sabotage, an invented slug, tests something else entirely: genblaze
# preflights unknown models and raises before spending a cent. Useful behaviour,
# and worth its own case (--preflight), but it never reaches a provider, so a
# fallback chain that only survives it has not been shown to survive anything.
# An invented slug. Genblaze preflights it, raises, and never reaches a provider —
# which is CS-5's own prescribed method ("invalid model ID") and the only
# sabotage that fails reliably.
#
# Two alternatives were tried first and both turned out to work:
#   seedance-2-0-fast-260128       ten raw submits gave five 200s and five 401s.
#                                  Flaky, not dead — the retry logic recovers
#                                  through it, which is correct behaviour and
#                                  useless as a sabotage.
#   seedance-2-0-260128-upscale    401s a raw generation payload but SUCCEEDS
#                                  through genblaze, because input_from supplies
#                                  the first_frame an upscaler wants. It returned
#                                  a real mp4.
# Every catalogued seedance slug tested works through the SDK. There is no real
# model that reliably refuses, so the sabotage has to be a fictional one.
SABOTAGED = "seedance-1-0-pro-fast-DOES-NOT-EXIST"
POISON = "kling-image2video-ALSO-DOES-NOT-EXIST"


def arg(flag: str, default: str) -> str:
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


def main() -> int:
    try:
        require("GMI_API_KEY", "B2_KEY_ID", "B2_APP_KEY")
    except ConfigError as exc:
        print(f"FAIL  {exc}")
        return 1

    sabotage = {int(n) for n in arg("--sabotage", "3,4").split(",") if n.strip()}
    doomed = {int(n) for n in arg("--doomed", "").split(",") if n.strip()}
    tl_id = arg("--through-line", "tower-signal")

    kit = load()
    entry = next(e for e in kit.through_lines["through_lines"] if e["id"] == tl_id)
    through_line = ThroughLine.from_kit(entry)
    prompts = [build_block_prompt(through_line, n, BLOCKS) for n in range(1, BLOCKS + 1)]

    for prompt in prompts:
        if not check(prompt).passed:
            print(f"BLOCKED block {prompt.block} — $0 spent")
            return 1

    image_provider, video_provider = GMICloudImageProvider(), GMICloudVideoProvider()
    register_all(image=image_provider, video=video_provider)
    register_seedance_ratio(video_provider)

    preflight: set[int] = set()

    def chain_for(n: int) -> list[str]:
        if n in doomed:
            return [SABOTAGED, POISON]
        if n in sabotage:
            return [SABOTAGED, *VIDEO_FALLBACKS]
        return [VIDEO_MODEL, *VIDEO_FALLBACKS]

    print(f"healthy   {VIDEO_MODEL} -> {VIDEO_FALLBACKS}")
    print(f"sabotaged blocks {sorted(sabotage) or '-'}: primary -> a dead slug, "
          f"fallback {VIDEO_FALLBACKS}")
    print(f"doomed    blocks {sorted(doomed) or '-'}: entire chain dead\n")

    async def all_blocks():
        return await asyncio.gather(*(
            run_block(
                p,
                image_provider=image_provider,
                video_provider=video_provider,
                sink_=sink(f"cs5-{tl_id}"),
                models=chain_for(p.block),
            )
            for p in prompts
        ), return_exceptions=True)

    results = asyncio.run(all_blocks())

    total, ready, fell_back = 0.0, 0, 0
    print(f"{'blk':<4}{'status':<9}{'cost':<9}{'model that ran':<32}attempts")
    print("-" * 96)
    for n, r in enumerate(results, start=1):
        if isinstance(r, Exception):
            print(f"{n:<4}{'ERROR':<9}{'-':<9}{type(r).__name__}: {str(r)[:60]}")
            continue
        total += r.cost_usd
        ready += r.ok
        fell_back += r.used_fallback
        trail = " -> ".join(f"{a['model'].split('/')[-1]}({a['status']})" for a in r.attempts)
        print(f"{n:<4}{r.status:<9}${r.cost_usd:<8.3f}{(r.video_model or '-'):<32}{trail}")
        if r.note:
            print(f"{'':<4}note: {r.note}")

    print("-" * 96)
    print(f"{ready}/{BLOCKS} ready · {fell_back} completed on a fallback · spend ${total:.3f}")

    # The acceptance criteria, asserted rather than eyeballed.
    ok = True
    for n in sorted((sabotage | preflight) - doomed):
        r = results[n - 1]
        if not (getattr(r, "ok", False) and r.used_fallback):
            print(f"FAIL  block {n} was sabotaged and did not complete on a fallback")
            ok = False
        elif r.video_model in VIDEO_FALLBACKS:
            print(f"OK    block {n} completed on {r.video_model}, recorded as the model that ran")
    for n in sorted(doomed):
        r = results[n - 1]
        if getattr(r, "ok", True):
            print(f"FAIL  block {n} had no working provider and still reported ready")
            ok = False
        else:
            print(f"OK    block {n} failed closed: {r.note}")
    healthy = [
        n for n in range(1, BLOCKS + 1)
        if n not in sabotage and n not in doomed and n not in preflight
    ]
    if all(getattr(results[n - 1], "video_model", None) == VIDEO_MODEL for n in healthy):
        print(f"OK    healthy blocks {healthy} stayed on the primary — no blanket fallback")
    else:
        print("FAIL  a healthy block fell back; the chain is firing when it should not")
        ok = False

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
