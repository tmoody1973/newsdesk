#!/usr/bin/env python3
"""MOO-416 — measure GMICloud's concurrency ceiling, and produce the style key.

Submits six image jobs at once and reads each step's real start/finish times to
see whether GMI ran them in parallel or queued them. Uses image rather than
video because the queue is per-API-key and images cost a fraction as much.

Dual purpose by design: the six outputs are style-key candidates for
b2://newsdesk-brand-kit (MOO-425), so nothing generated here is thrown away.

    uv run python scripts/spike_concurrency.py
"""

from __future__ import annotations

import asyncio
import sys
import time

from genblaze_core import KeyStrategy, Modality, ObjectStorageSink, Pipeline
from genblaze_gmicloud import GMICloudImageProvider

from newsdesk.config import BUCKETS, ConfigError, backend, require

N = 6
MODEL = "seedream-5.0-lite"
ASPECT = "9:16"

# Verbatim from ~/.claude/skills/vox-motion-graphics/references/vox-prompts.md.
# Six candidates from one prompt; the best becomes brand-kit/style-key.png.
STYLE_KEY_PROMPT = (
    "Editorial mixed-media collage style swatch, Vox-documentary motion graphics "
    "aesthetic: flat warm yellow and off-white paper background with halftone dot "
    "texture, archival photo cutouts with rough white paper borders, torn paper "
    "edges and tape strips, hand-drawn black marker circles and arrows, bold flat "
    "color blocks in navy and coral, subtle paper grain and drop shadows. "
    "Abstract composition only — no characters, no objects with faces, no letters, "
    "no words, no numbers. Non-photorealistic, no live-action, no realism, "
    "no 3D render."
)


def main() -> None:
    try:
        require("GMI_API_KEY", "B2_KEY_ID", "B2_APP_KEY")
    except ConfigError as exc:
        sys.exit(f"FAIL  {exc}")

    sink = ObjectStorageSink(
        backend(BUCKETS["brand_kit"]),
        prefix="style-key-candidates",
        key_strategy=KeyStrategy.HIERARCHICAL,
    )

    pipeline = Pipeline("style-key-spike").step(
        GMICloudImageProvider(),
        model=MODEL,
        prompt=STYLE_KEY_PROMPT,
        modality=Modality.IMAGE,
        aspect_ratio=ASPECT,
    )

    print(f"submitting {N}× {MODEL} at {ASPECT}, max_concurrency={N}\n")
    wall_start = time.monotonic()
    results = asyncio.run(
        pipeline.abatch_run(
            prompts=[STYLE_KEY_PROMPT] * N,
            max_concurrency=N,
            sink=sink,
            fail_fast=False,
            raise_on_failure=False,
            timeout=600,
        )
    )
    wall = time.monotonic() - wall_start

    spans: list[tuple[float, float]] = []
    total_cost = 0.0
    ok = 0

    for i, res in enumerate(results, 1):
        step = res.run.steps[0]
        started, ended = step.started_at, step.completed_at
        cost = getattr(step, "cost_usd", None)
        if cost:
            total_cost += cost
        status = getattr(step, "status", "?")
        if started and ended:
            spans.append((started.timestamp(), ended.timestamp()))
            dur = (ended - started).total_seconds()
            print(f"  {i}  {status}  {dur:6.1f}s  cost={cost}")
        else:
            print(f"  {i}  {status}  (no timing)")
        if step.assets:
            ok += 1
            print(f"     {step.assets[0].url}")

    print(f"\nwall clock        {wall:.1f}s for {N} jobs")
    print(f"completed         {ok}/{N}")
    print(f"reported cost     {total_cost if total_cost else 'not reported by connector'}")

    if spans:
        # Peak overlap = the real ceiling. Sum of durations vs wall clock tells
        # us serial (ratio ~1) from parallel (ratio ~N).
        edges = sorted([(s, 1) for s, _ in spans] + [(e, -1) for _, e in spans])
        peak = cur = 0
        for _, delta in edges:
            cur += delta
            peak = max(peak, cur)
        serial = sum(e - s for s, e in spans)
        print(f"peak concurrent   {peak}  (requested {N})")
        print(f"speedup           {serial / wall:.1f}× vs serial")
        print(
            f"\nVERDICT: {'parallel' if peak >= N else f'queued at {peak}'} — "
            f"a 6-block story's image half takes ~{wall:.0f}s"
        )


if __name__ == "__main__":
    main()
