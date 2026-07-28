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

# The chain is inverted from what the design assumed, and every line of this is
# measured rather than reasoned:
#
#   seedance-1-0-pro-fast          404 — the undated slug does not exist. GMI
#                                  carries dated builds; example_slugs are real.
#   seedance-1-0-pro-fast-251015   returned 1248x704 LANDSCAPE with a portrait
#                                  first_frame. Read at the time as "the model
#                                  ignores aspect ratio". It was not — genblaze
#                                  emits `aspect_ratio` and GMI reads `ratio`, so
#                                  the parameter arrived under a name nothing
#                                  looked at (see register_seedance_ratio).
#                                  With the alias: 704x1248, TRUE 9:16, $0.022.
#   seedance-2-0-260128            500 "Backend error (401)" at $0
#   seedance-2-0-fast-260128       500 "Backend error (401)" at $0. This is the
#                                  slug GMI's docs actually name; genblaze's
#                                  example_slugs give the undated one, which the
#                                  docs do not carry.
#
#   Both 2.0 generation models were retried with a RAW doc-exact request, no SDK
#   in the path, and both 401 identically — so it is not genblaze's payload. The
#   control that pins it down is seedance-2-0-260128-upscale: same org, same key,
#   same endpoint, and it returns 400 rather than 401. A validation error means
#   the request reached the backend and was understood. So this is not a blanket
#   account problem; entitlement is missing on the two 2.0 generation models
#   specifically, upstream of GMI. A waitlist form will not move it — GMI support
#   has to provision it. Not in VIDEO_FALLBACKS, because falling back to a
#   guaranteed 401 only burns a retry; they are listed in SEEDANCE_SLUGS purely
#   so the ratio alias is already registered if access ever appears.
#   kling-image2video-v1.6-pro     404, not in the catalogue.
#   kling-image2video-v2.1-master  720x1280, TRUE 9:16, 10.4s, $0.28 — works with
#                                  no alias needed, at 12.7x the seedance price.
#
# So seedance leads and Kling is the fallback that needs no special handling.
# Six blocks of video is $0.13 rather than $1.68.
VIDEO_MODEL = os.getenv("NEWSDESK_VIDEO_MODEL", "seedance-1-0-pro-fast-251015")
VIDEO_FALLBACKS = os.getenv(
    "NEWSDESK_VIDEO_FALLBACKS", "kling-image2video-v2.1-master"
).split(",")

SEEDANCE_SLUGS = (
    "seedance-1-0-pro-fast-251015",
    "seedance-2-0-fast-260128",
    "seedance-2-0-260128",
    "seedance-1-0-pro-250528",
)

ASPECT_RATIO = "9:16"
DURATION_S = 10

# Vertical delivery. Passed explicitly on every call because the vox skill
# documented, and MOO-424 reproduced on GMI, that framing does not inherit
# between steps.
IMAGE_PARAMS: dict[str, Any] = {"aspect_ratio": ASPECT_RATIO}


def register_seedance_ratio(provider: Any) -> None:
    """Teach the seedance specs GMI's native name for aspect ratio.

    Genblaze normalizes the canonical param to `aspect_ratio` and the seedance
    family's allowlist accepts it — but GMI's own docs for both
    `seedance-1-0-pro-fast-251015` and `seedance-2-0-fast-260128` call it
    **`ratio`**. There is no alias between the two, so `aspect_ratio` reached the
    wire under a name the API does not read, was ignored, and the job fell back
    to its 16:9 default. That is how a request for 9:16 with a portrait
    `first_frame` returned 1248x704: not a model refusing vertical, a parameter
    arriving under the wrong name.

    Same shape as the `guidance_scale` → `cfg_scale` alias the family already
    carries; this one is simply missing. Registered here rather than patched
    upstream so the fix ships with the app and is visible in the run's params.
    """
    import dataclasses

    for slug in SEEDANCE_SLUGS:
        try:
            spec = provider.models.get(slug)
        except Exception:  # noqa: BLE001 — a slug this account lacks is not fatal
            continue
        provider.models.register(
            dataclasses.replace(
                spec,
                param_aliases={**(spec.param_aliases or {}), "aspect_ratio": "ratio"},
                param_allowlist=frozenset(spec.param_allowlist or ()) | {"ratio"},
            ),
            override=True,
        )


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
