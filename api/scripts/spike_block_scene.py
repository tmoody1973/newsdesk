#!/usr/bin/env python3
"""Settle two questions with one cheap batch: aspect ratio, and archival cutouts.

Runs a real CS-1 block-1 SCENE prompt — not the abstract style swatch — across
three model/param combinations. The swatch deliberately forbids content ("no
characters, no objects with faces"), so it could never have shown whether the
model renders archival photo cutouts. This can.

    uv run python scripts/spike_block_scene.py

~$0.12 total. Prints measured dimensions and real per-asset cost.
"""

from __future__ import annotations

import asyncio
import io
import sys
import urllib.request

from genblaze_core import KeyStrategy, Modality, ObjectStorageSink, Pipeline
from genblaze_gmicloud import GMICloudImageProvider
from PIL import Image

from newsdesk.config import BUCKETS, ConfigError, backend, require
from newsdesk.pricing import register_all

# Verbatim style tokens from vox-motion-graphics/references/vox-prompts.md.
STYLE_TOKENS = (
    "editorial mixed-media collage, archival photo cutouts with white paper borders, "
    "flat bold color fields, halftone and paper grain textures, hand-drawn marker "
    "annotations, non-photorealistic, no live-action"
)

# The fixed NEGATIVE line — a policy constant, copied verbatim.
NEGATIVE = (
    "readable text, letters, words, numbers, captions, subtitles, watermark, logo, "
    "photorealism, live-action footage, 3D render, lip-sync, talking characters, "
    "color drift"
)

# CS-1 block 1: the rescission of $1.1B in public broadcasting funding.
# Through-line object is the broadcast tower's shrinking signal rings.
SCENE = (
    "A warm cream paper background with halftone dot texture. An archival photo cutout "
    "of a tall broadcast tower with rough torn white paper borders stands at center, "
    "taped down at one corner. Concentric hand-drawn marker rings radiate outward from "
    "its top, the outermost ones faint and breaking apart. Torn-paper fragments of "
    "banknotes drift downward and settle in a small pile at the tower's base. A thick "
    "black marker circle is drawn around the innermost surviving ring. Flat navy and "
    "coral paper shapes anchor the lower corners."
)

PROMPT = f"STYLE REFERENCE: {STYLE_TOKENS}.\nSCENE: {SCENE}\nNEGATIVE: {NEGATIVE}"

# Each variant isolates one hypothesis about why 9:16 was ignored.
VARIANTS = [
    ("seedream-5.0-lite", {"aspect_ratio": "9:16", "resolution": "1080p"},
     "does resolution alongside aspect_ratio change anything?"),
    ("gemini-2.5-flash-image", {"aspect_ratio": "9:16"},
     "does a different model honor aspect_ratio?"),
    ("flux-kontext-pro", {"aspect_ratio": "9:16"},
     "does the in-context model honor it, and render cutouts?"),
]


def measure(url: str) -> str:
    try:
        with urllib.request.urlopen(url, timeout=60) as r:  # noqa: S310 — B2 URL we built
            im = Image.open(io.BytesIO(r.read()))
        ratio = im.width / im.height
        target = 9 / 16
        verdict = "9:16 ✓" if abs(ratio - target) < 0.02 else f"NOT 9:16 (ratio {ratio:.2f})"
        return f"{im.width}x{im.height}  {verdict}"
    except Exception as exc:  # noqa: BLE001 — reporting a probe, not masking a bug
        return f"could not measure: {exc}"


def main() -> None:
    try:
        require("GMI_API_KEY", "B2_KEY_ID", "B2_APP_KEY")
    except ConfigError as exc:
        sys.exit(f"FAIL  {exc}")

    provider = GMICloudImageProvider()
    register_all(image=provider)

    sink = ObjectStorageSink(
        backend(BUCKETS["assets"]),
        prefix="spike-block-scene",
        key_strategy=KeyStrategy.HIERARCHICAL,
    )

    async def run_one(model: str, params: dict, why: str):
        pipe = Pipeline(f"block-scene-{model}").step(
            provider, model=model, prompt=PROMPT, modality=Modality.IMAGE, **params
        )
        try:
            return model, why, await pipe.arun(sink=sink, raise_on_failure=False, timeout=600)
        except Exception as exc:  # noqa: BLE001
            return model, why, exc

    async def run_all():
        return await asyncio.gather(*(run_one(*v) for v in VARIANTS))

    print(f"{len(VARIANTS)} variants, one CS-1 block-1 scene prompt\n")
    total = 0.0
    for model, why, res in asyncio.run(run_all()):
        print(f"=== {model}")
        print(f"    {why}")
        if isinstance(res, Exception):
            print(f"    FAILED {type(res).__name__}: {str(res)[:140]}\n")
            continue
        step = res.run.steps[0]
        cost = getattr(step, "cost_usd", None) or 0.0
        total += cost
        print(f"    status {step.status}   cost ${cost:.3f}")
        if step.assets:
            url = step.assets[0].url
            print(f"    {measure(url)}")
            print(f"    {url}")
        print()

    print(f"batch cost ${total:.3f}")


if __name__ == "__main__":
    main()
