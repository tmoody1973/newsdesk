#!/usr/bin/env python3
"""One block, end to end, on the cheap video model (MOO-424).

    uv run python scripts/spike_one_block.py [--through-line tower-signal] [--block 1]

~$0.06: one gemini image plus one seedance-1-0-pro-fast clip. The point is to
prove the wire before spending six times that, and specifically to answer the
three things the issue says must be verified rather than assumed:

  1. does the styled still actually arrive as `first_frame` on the video call?
  2. is `aspect_ratio` honoured, measured from the returned asset?
  3. does the manifest name the model that *ran*, including on fallback?

Prints the resolved Step params so the routing can be read rather than trusted.
"""

from __future__ import annotations

import asyncio
import sys

from genblaze_gmicloud import GMICloudImageProvider, GMICloudVideoProvider

from newsdesk.blocks import VIDEO_FALLBACKS, VIDEO_MODEL, build_pipeline, read_result, sink
from newsdesk.config import ConfigError, require
from newsdesk.policy.gate import check
from newsdesk.pricing import register_all
from newsdesk.scene import ThroughLine, build_block_prompt
from newsdesk.brandkit import load


def arg(flag: str, default: str) -> str:
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


def main() -> int:
    try:
        require("GMI_API_KEY", "B2_KEY_ID", "B2_APP_KEY")
    except ConfigError as exc:
        print(f"FAIL  {exc}")
        return 1

    tl_id, n = arg("--through-line", "tower-signal"), int(arg("--block", "1"))

    kit = load()
    entry = next(
        (e for e in kit.through_lines["through_lines"] if e["id"] == tl_id), None
    )
    if entry is None:
        print(f"FAIL  no such through-line: {tl_id}")
        return 1

    prompt = build_block_prompt(ThroughLine.from_kit(entry), n)

    # Wall 2 before Wall 2's cost. Nothing paid happens on a blocked prompt, and
    # that has to be true of a spike script too or the guarantee is decorative.
    gate = check(prompt)
    if not gate.passed:
        print(f"BLOCKED by policy — $0 spent\n{gate.explain()}")
        return 1
    print(f"gate: {len(gate.findings)} rules checked, all passed\n")
    print(prompt.render(), "\n")

    image_provider, video_provider = GMICloudImageProvider(), GMICloudVideoProvider()
    register_all(image=image_provider, video=video_provider)

    pipe = build_pipeline(
        prompt, image_provider=image_provider, video_provider=video_provider
    )

    run = asyncio.run(pipe.arun(sink=sink(f"spike-block-{n}"), raise_on_failure=False, timeout=900))
    result = read_result(n, run, requested_video_model=VIDEO_MODEL)

    print(f"status        {result.status}")
    print(f"still         {result.still_uri}")
    print(f"  sha256      {result.still_sha256}")
    print(f"clip          {result.clip_uri}")
    print(f"  sha256      {result.clip_sha256}")
    print(f"image model   {result.image_model}")
    print(f"video model   {result.video_model}"
          f"{'  (FALLBACK — asked for ' + VIDEO_MODEL + ')' if result.used_fallback else ''}")
    print(f"fallbacks     {VIDEO_FALLBACKS}")
    print(f"cost          ${result.cost_usd:.3f}")
    if result.note:
        print(f"note          {result.note}")

    # What actually went on the wire, read back rather than assumed.
    video_step = run.run.steps[1]
    print(f"\nvideo step inputs: {[getattr(a, 'url', a) for a in (video_step.inputs or ())]}")
    print(f"video step params: {video_step.params}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
