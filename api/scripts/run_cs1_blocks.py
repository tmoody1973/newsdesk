#!/usr/bin/env python3
"""Six-block CS-1 generation (MOO-424).

    uv run python scripts/run_cs1_blocks.py [--through-line tower-signal] [--stills-only]

~$1.91 on the verified chain: six gemini stills at $0.039 and six Kling clips at
$0.28. `--stills-only` runs the image leg for $0.23, which is the cheap way to
judge the thing that actually matters — whether six independently generated
stills read as one video.

Every block passes the deterministic gate before any paid call. Blocks run
concurrently: the MOO-418 spike measured no ceiling at six on the image
endpoint, 5.2x speedup, 66.8s wall clock.
"""

from __future__ import annotations

import asyncio
import sys

from genblaze_gmicloud import GMICloudImageProvider, GMICloudVideoProvider

from newsdesk.blocks import (
    IMAGE_MODEL,
    IMAGE_PARAMS,
    VIDEO_FALLBACKS,
    VIDEO_MODEL,
    BlockError,
    build_pipeline,
    read_result,
    sink,
)
from newsdesk.brandkit import load
from newsdesk.config import ConfigError, require
from newsdesk.policy.gate import check
from newsdesk.pricing import register_all
from newsdesk.scene import ThroughLine, build_block_prompt

BLOCKS = 6


def arg(flag: str, default: str) -> str:
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


def main() -> int:
    try:
        require("GMI_API_KEY", "B2_KEY_ID", "B2_APP_KEY")
    except ConfigError as exc:
        print(f"FAIL  {exc}")
        return 1

    stills_only = "--stills-only" in sys.argv
    tl_id = arg("--through-line", "tower-signal")

    kit = load()
    entry = next((e for e in kit.through_lines["through_lines"] if e["id"] == tl_id), None)
    if entry is None:
        print(f"FAIL  no such through-line: {tl_id}")
        return 1
    through_line = ThroughLine.from_kit(entry)

    prompts = [build_block_prompt(through_line, n, BLOCKS) for n in range(1, BLOCKS + 1)]

    # Wall 2 before a cent is spent, on every block, not a sample.
    for prompt in prompts:
        gate = check(prompt)
        if not gate.passed:
            print(f"BLOCKED block {prompt.block} — $0 spent\n{gate.explain()}")
            return 1
    print(f"gate: {BLOCKS} blocks × {len(check(prompts[0]).findings)} rules, all passed")

    image_provider = GMICloudImageProvider()
    video_provider = GMICloudVideoProvider()
    register_all(image=image_provider, video=video_provider)

    print(f"through-line  {through_line.label}")
    print(f"image         {IMAGE_MODEL} {IMAGE_PARAMS}")
    if stills_only:
        print("video         skipped (--stills-only)\n")
    else:
        print(f"video         {VIDEO_MODEL}  fallbacks={VIDEO_FALLBACKS}\n")

    async def one(prompt):
        if stills_only:
            from genblaze_core import Modality, Pipeline

            pipe = Pipeline(f"block-{prompt.block}").step(
                image_provider, model=IMAGE_MODEL, prompt=prompt.render_for_image(),
                modality=Modality.IMAGE, **IMAGE_PARAMS,
            )
        else:
            pipe = build_pipeline(
                prompt, image_provider=image_provider, video_provider=video_provider
            )
        try:
            res = await pipe.arun(
                sink=sink(f"cs1-{tl_id}"), raise_on_failure=False, timeout=1200
            )
            return prompt.block, res, None
        except Exception as exc:  # noqa: BLE001
            return prompt.block, None, exc

    async def all_blocks():
        return await asyncio.gather(*(one(p) for p in prompts))

    results = asyncio.run(all_blocks())

    total, failures = 0.0, 0
    for n, res, exc in sorted(results, key=lambda r: r[0]):
        if exc is not None:
            print(f"block {n}  ERROR {type(exc).__name__}: {str(exc)[:120]}")
            failures += 1
            continue
        if stills_only:
            step = res.run.steps[0]
            cost = float(getattr(step, "cost_usd", None) or 0.0)
            total += cost
            url = step.assets[0].url if step.assets else None
            print(f"block {n}  {step.status}  ${cost:.3f}  {url}")
            failures += 0 if url else 1
            continue
        try:
            r = read_result(n, res, requested_video_model=VIDEO_MODEL)
        except BlockError as e:
            print(f"block {n}  HARD STOP — {e}")
            failures += 1
            continue
        total += r.cost_usd
        flag = "  FALLBACK" if r.used_fallback else ""
        print(f"block {n}  {r.status}  ${r.cost_usd:.3f}  {r.video_model}{flag}")
        print(f"          still {r.still_uri}")
        print(f"          clip  {r.clip_uri}")
        failures += 0 if r.ok else 1

    print(f"\n{BLOCKS - failures}/{BLOCKS} blocks ready · spend ${total:.3f}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
