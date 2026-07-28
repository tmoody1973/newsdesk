"""The generation core — one block, two steps (MOO-424, P0-4).

An image step makes the styled still; a video step animates from it as
`first_frame` via `input_from`. Two modalities in one Genblaze `Pipeline`, with
`fallback_models` on the video leg.

**The style key is not an input here, and that is the whole finding.** MOO-424
tested it: two scenes generated from one style key produced a solid blue ground
and a warm tan one, while naming the palette explicitly in text locked it. So
the image step is text-only and style lives in `brand-kit/style-tokens.txt`
under version control, rather than in a generated artifact that drifts.

Why an image step survives at all, given that: no GMI video model exposes a
style-reference slot — every family routes images to keyframe slots only
(`first_frame`/`last_frame` for seedance, `image` for the rest). Style therefore
has to be carried *by a frame*, and a clip that begins on a frame which is the
style is a stronger guarantee than a reference attached to a video call. It also
makes the MOO-429 retry cheap: re-rolling a still costs cents, re-rolling video
costs dollars.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from genblaze_core import KeyStrategy, Modality, ObjectStorageSink, Pipeline
from genblaze_core.models.enums import StepStatus

from newsdesk.blockprompt import BlockPrompt
from newsdesk.config import BUCKETS, backend

# Settled by measurement, not preference. `seedream-5.0-lite` silently ignores
# `aspect_ratio` and returns 2048x2048 regardless; `gemini-2.5-flash-image`
# honours it and returned 768x1344.
IMAGE_MODEL = os.getenv("NEWSDESK_IMAGE_MODEL", "gemini-2.5-flash-image")

# Default to the cheap one. seedance-1-0-pro-fast is $0.022/asset against
# seedance-2.0's $0.52 for ten seconds — a full story is $0.94 versus $3.95. The
# expensive model is for the hero run and the demo, not for iteration.
# The undated slug 404s: "model seedance-1-0-pro-fast does not exist". GMI
# carries dated builds and the registry's example_slugs are the real names.
VIDEO_MODEL = os.getenv("NEWSDESK_VIDEO_MODEL", "seedance-1-0-pro-fast-251015")
VIDEO_FALLBACKS = os.getenv(
    "NEWSDESK_VIDEO_FALLBACKS", "kling-image2video-v2.1-master"
).split(",")

ASPECT_RATIO = "9:16"
DURATION_S = 10

# Vertical delivery. Passed explicitly on every call because the vox skill
# documented, and MOO-424 reproduced on GMI, that framing does not inherit
# between steps.
IMAGE_PARAMS: dict[str, Any] = {"aspect_ratio": ASPECT_RATIO}


class BlockError(RuntimeError):
    """Raised when a block cannot be produced and the run must not continue."""


@dataclass(frozen=True)
class BlockResult:
    """What one block produced, and who actually produced it.

    `video_model` is read back from the completed step rather than echoed from
    the request, because the fallback chain is only honest if the manifest
    records the provider that *ran* — not the one that was asked first.
    """

    n: int
    still_uri: str | None = None
    still_sha256: str | None = None
    clip_uri: str | None = None
    clip_sha256: str | None = None
    image_model: str | None = None
    video_model: str | None = None
    used_fallback: bool = False
    cost_usd: float = 0.0
    status: str = "ready"
    note: str | None = None

    @property
    def ok(self) -> bool:
        return self.status == "ready"


def sink(prefix: str) -> ObjectStorageSink:
    """Assets land in the public bucket under a per-run hierarchy."""
    return ObjectStorageSink(
        backend(BUCKETS["assets"]), prefix=prefix, key_strategy=KeyStrategy.HIERARCHICAL
    )


def build_pipeline(
    prompt: BlockPrompt,
    *,
    image_provider: Any,
    video_provider: Any,
    video_model: str = VIDEO_MODEL,
    fallbacks: list[str] | None = None,
    duration: int = DURATION_S,
) -> Pipeline:
    """The two-step chain for one block.

    `input_from=0` is what routes the still into the video call. For seedance it
    lands in `first_frame`, because `gmi-video-seedance` declares
    `route_images(slots=("first_frame", "last_frame"))`; for the kling fallback
    it lands in `image`. Neither name is passed by us, and that is the point —
    the family owns the mapping, so a fallback to a differently-shaped model does
    not need a second code path.
    """
    return (
        Pipeline(f"block-{prompt.block}")
        .step(
            image_provider,
            model=IMAGE_MODEL,
            prompt=prompt.render_for_image(),
            modality=Modality.IMAGE,
            **IMAGE_PARAMS,
        )
        .step(
            video_provider,
            model=video_model,
            prompt=prompt.render(),
            modality=Modality.VIDEO,
            fallback_models=list(fallbacks if fallbacks is not None else VIDEO_FALLBACKS),
            input_from=0,
            duration=duration,
            aspect_ratio=ASPECT_RATIO,
        )
    )


def _asset(step: Any) -> tuple[str | None, str | None]:
    assets = getattr(step, "assets", None) or ()
    if not assets:
        return None, None
    return getattr(assets[0], "url", None), getattr(assets[0], "sha256", None)


def read_result(n: int, result: Any, *, requested_video_model: str) -> BlockResult:
    """Turn a completed run into a block record, refusing partial success.

    An image failure is a hard stop rather than a degraded path: animating from
    an unstyled frame produces a clip that is off-house and expensive, and the
    only thing worse than a failed run is a run that quietly changed style.

    Accepts either a `PipelineResult` or the `Run` inside it. `arun()` returns
    the former and reading `.steps` off it silently yields nothing — which
    surfaced as "pipeline produced 0 step(s)" on a run where the image step had
    actually succeeded and been paid for.
    """
    run = getattr(result, "run", result)
    steps = list(getattr(run, "steps", ()) or ())
    if len(steps) < 2:
        return BlockResult(n=n, status="failed", note=f"pipeline produced {len(steps)} step(s)")

    image_step, video_step = steps[0], steps[1]
    cost = sum(float(getattr(s, "cost_usd", None) or 0.0) for s in steps)

    still_uri, still_sha = _asset(image_step)
    # Compared against the SDK's own enum rather than a guessed vocabulary. The
    # first version accepted "completed"/"success"/"ok" and rejected a step whose
    # status was literally StepStatus.SUCCEEDED — a hard stop on a healthy run.
    if getattr(image_step, "status", None) != StepStatus.SUCCEEDED or not still_uri:
        raise BlockError(
            f"block {n}: the style still failed ({getattr(image_step, 'status', '?')}). "
            f"Refusing to animate from an unstyled frame."
        )

    clip_uri, clip_sha = _asset(video_step)
    actual_model = getattr(video_step, "model", None) or requested_video_model

    if not clip_uri:
        # Both the primary and every fallback are exhausted by this point —
        # Genblaze walks the chain inside the step. The block stops here and the
        # run pauses; it never proceeds with five clips and a gap.
        return BlockResult(
            n=n, still_uri=still_uri, still_sha256=still_sha, image_model=IMAGE_MODEL,
            video_model=actual_model, cost_usd=round(cost, 4), status="failed",
            note=f"every video provider failed (last: {actual_model}, "
                 f"status {getattr(video_step, 'status', '?')})",
        )

    return BlockResult(
        n=n,
        still_uri=still_uri,
        still_sha256=still_sha,
        clip_uri=clip_uri,
        clip_sha256=clip_sha,
        image_model=IMAGE_MODEL,
        video_model=actual_model,
        used_fallback=actual_model != requested_video_model,
        cost_usd=round(cost, 4),
        status="ready",
    )
