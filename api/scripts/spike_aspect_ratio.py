#!/usr/bin/env python3
"""Which video model actually honours 9:16? (MOO-424)

    uv run python scripts/spike_aspect_ratio.py

`seedance-1-0-pro-fast-251015` returned 1248x704 with `aspect_ratio="9:16"` on
the wire and a 768x1344 portrait `first_frame`. It ignored both. This is the
same failure the image side had with `seedream-5.0-lite`, where the fix turned
out to be a model swap rather than a parameter.

Reuses the still from the earlier spike as `external_inputs` rather than
regenerating it, so both models animate the *identical* frame and the only
variable is the model. Saves an image call, and makes the comparison honest.

~$0.80: one seedance-2.0 clip ($0.52) and one Kling clip ($0.28). Measures the
returned dimensions with ffprobe rather than trusting the request.
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

from genblaze_core import Asset, Modality, Pipeline
from genblaze_gmicloud import GMICloudVideoProvider

from newsdesk.blocks import ASPECT_RATIO, DURATION_S, register_seedance_ratio, sink
from newsdesk.config import ConfigError, require
from newsdesk.pricing import register_all
from newsdesk.scene import ThroughLine, build_block_prompt
from newsdesk.brandkit import load

# The still from spike_one_block.py — on-house, portrait, already paid for.
STILL_URL = (
    "https://s3.us-east-005.backblazeb2.com/newsdesk-assets/spike-block-1/runs/"
    "2026-07-28/a795c927-7a93-4fd7-9f62-89e9a8b7e917/assets/"
    "ca82e2d6-4650-4a04-a923-b5a8782c3637.png"
)
STILL_SHA = "1c10765f67352f3c1a53b0855f78f5ad6169383f57be49019babd1ee22200426"

# GMI's seedance docs use `ratio`, not `aspect_ratio`. The earlier landscape
# result was this parameter being silently ignored, not the model refusing 9:16.
CANDIDATES = [
    ("seedance-1-0-pro-fast-251015", "with aspect_ratio aliased to GMI's `ratio`"),
]


def measure(url: str) -> str:
    """Real dimensions off the returned file. The request is not evidence."""
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as fh:
            with urllib.request.urlopen(url, timeout=180) as r:  # noqa: S310 — our B2 URL
                fh.write(r.read())
            path = Path(fh.name)
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
             "stream=width,height,duration", "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        w, h, dur = (out.split(",") + ["", "", ""])[:3]
        ratio = int(w) / int(h)
        verdict = "9:16 PORTRAIT ✓" if abs(ratio - 9 / 16) < 0.03 else f"NOT 9:16 (ratio {ratio:.3f})"
        path.unlink(missing_ok=True)
        return f"{w}x{h}  {float(dur):.1f}s  {verdict}"
    except Exception as exc:  # noqa: BLE001 — reporting a probe, not masking a bug
        return f"could not measure: {type(exc).__name__}: {exc}"


def main() -> int:
    try:
        require("GMI_API_KEY", "B2_KEY_ID", "B2_APP_KEY")
    except ConfigError as exc:
        print(f"FAIL  {exc}")
        return 1

    kit = load()
    entry = next(e for e in kit.through_lines["through_lines"] if e["id"] == "tower-signal")
    prompt = build_block_prompt(ThroughLine.from_kit(entry), 1)

    still = Asset(url=STILL_URL, sha256=STILL_SHA, media_type="image/png")
    provider = GMICloudVideoProvider()
    register_all(video=provider)
    register_seedance_ratio(provider)

    print(f"first_frame  {STILL_URL.rsplit('/', 1)[-1]}  (768x1344 portrait, reused)")
    print(f"asking for   ratio={ASPECT_RATIO}  resolution=720p  duration={DURATION_S}\n")

    async def run_one(model: str, why: str):
        pipe = Pipeline(f"aspect-{model}").step(
            provider,
            model=model,
            prompt=prompt.render(),
            modality=Modality.VIDEO,
            external_inputs=[still],
            duration=DURATION_S,
            aspect_ratio=ASPECT_RATIO,
            resolution="720p",
        )
        try:
            res = await pipe.arun(
                sink=sink("spike-aspect"), raise_on_failure=False, timeout=900
            )
            return model, why, res
        except Exception as exc:  # noqa: BLE001
            return model, why, exc

    async def run_all():
        return await asyncio.gather(*(run_one(m, w) for m, w in CANDIDATES))

    results = asyncio.run(run_all())

    total = 0.0
    for model, why, res in results:
        print(f"=== {model}\n    {why}")
        if isinstance(res, Exception):
            print(f"    FAILED {type(res).__name__}: {str(res)[:160]}\n")
            continue
        step = res.run.steps[0]
        cost = float(getattr(step, "cost_usd", None) or 0.0)
        total += cost
        print(f"    status {step.status}   cost ${cost:.3f}")
        if step.assets:
            print(f"    {measure(step.assets[0].url)}")
            print(f"    {step.assets[0].url}")
        print()

    print(f"batch cost ${total:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
