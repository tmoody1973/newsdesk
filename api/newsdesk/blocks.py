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

import asyncio
import os
from dataclasses import dataclass, field, replace
from typing import Any

from genblaze_core import Asset, KeyStrategy, Modality, ObjectStorageSink, Pipeline
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


# Attempts per model before moving down the chain, and the waits between them.
#
# Measured 2026-07-28: ten raw submits to seedance-2-0-fast-260128 returned five
# 200s and five 500 "Backend error (401)". Not an entitlement gap — GMI's upstream
# credential appears to load-balance across pool members, some unauthorized. The
# same run saw blocks 3 and 4 complete on that model while block 5 failed on it.
#
# A flaky provider is not a dead one, and answering a transient 401 by switching
# models is the wrong move twice over: it abandons a working model, and it bills
# the fallback's higher rate for a failure that would have cleared on retry.
# Same model first, then down the chain.
RETRY_DELAYS_S = (2, 6, 15)

# "timed out" as well as "timeout": httpx says "read operation timed out", and a
# list carrying only the one-word form silently classifies every timeout as
# permanent. Caught by the table in tests/test_blocks.py.
#
# "rate_limit" for the same reason on a different provider: genblaze's
# ElevenLabs adapter classifies a throttle to `code=rate_limit` and the status
# code never appears in the message, so a list carrying only "429" read the most
# transient failure there is as permanent. Measured on the CS-1 narration run of
# 2026-07-28 — six concurrent takes, and blocks fell to LMNT on the first refusal
# with no retry at all.
_TRANSIENT = (
    "401", "403", "429", "500", "502", "503", "504",
    "timeout", "timed out", "temporarily", "overloaded", "rate_limit",
)


def _is_transient(exc: Exception | str) -> bool:
    """Whether a failure is worth trying the same model again for.

    Deliberately treats 401/403 as transient, which is wrong in general and right
    here: GMI wraps an upstream authorization failure as a 500 body, and the same
    key succeeds on the next call half the time. A genuinely revoked key fails
    every attempt and still walks the chain — it just costs three tries first.
    """
    text = str(exc).lower()
    return any(t in text for t in _TRANSIENT)


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
    # Every model tried, in order, with what it did. The fallback chain is only
    # an honest claim if the record shows what was attempted, not just what won.
    attempts: tuple[dict[str, Any], ...] = field(default_factory=tuple)

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


def video_only_pipeline(
    prompt: BlockPrompt,
    still: Any,
    *,
    video_provider: Any,
    model: str,
    duration: int = DURATION_S,
) -> Pipeline:
    """Re-animate an existing still. The retry leg of the fallback chain.

    Seeded with `external_inputs` rather than `input_from`, because the still
    already exists and already cost money. Re-running the two-step pipeline to
    change video models would regenerate a perfectly good image and, worse,
    produce a *different* one — so the retry would silently change the block's
    look as well as its provider.
    """
    return Pipeline(f"block-{prompt.block}-retry-{model}").step(
        video_provider,
        model=model,
        prompt=prompt.render(),
        modality=Modality.VIDEO,
        external_inputs=[still],
        duration=duration,
        aspect_ratio=ASPECT_RATIO,
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


async def run_block(
    prompt: BlockPrompt,
    *,
    image_provider: Any,
    video_provider: Any,
    sink_: Any,
    models: list[str] | None = None,
    duration: int = DURATION_S,
    timeout: int = 1200,
) -> BlockResult:
    """One block, walking the model chain ourselves.

    Genblaze carries `fallback_models` and it is still passed through below, but
    it fires only on `ProviderErrorCode.MODEL_ERROR` — and its classifier reaches
    that branch only for messages containing "not found" or "not available",
    *after* auth and server checks have already claimed anything with 401, 403,
    400, 500, 502 or 503 in it. GMI says "model X does not exist" over HTTP 404,
    which lands in UNKNOWN. Measured: a bad slug with Kling registered as a
    fallback failed outright and never attempted it.

    So the chain is walked here as well. The SDK's version stays as the inner
    layer — when it does fire it is cheaper, retrying inside the same run — and
    this is the outer one that catches everything the classifier files elsewhere.
    Without it `fallback_models` is decoration on the one story it exists to
    tell, and CS-5 would pass by never engaging.

    The retry re-animates the *existing* still rather than re-running both steps.
    Regenerating the image would cost twice and produce a different picture, so a
    provider substitution would silently change the block's look as well as its
    lineage.
    """
    chain = list(models if models is not None else [VIDEO_MODEL, *VIDEO_FALLBACKS])
    attempts: list[dict[str, Any]] = []
    block: BlockResult | None = None
    still: Any = None
    spent = 0.0  # every attempt, including the ones that produced nothing usable

    for model in chain:
      for attempt_n in range(len(RETRY_DELAYS_S) + 1):
        if attempt_n:
            await asyncio.sleep(RETRY_DELAYS_S[attempt_n - 1])
        try:
            if still is None:
                # Nothing salvageable yet, so both steps run. This is the first
                # attempt, or a previous one died before producing a still.
                result = await build_pipeline(
                    prompt,
                    image_provider=image_provider,
                    video_provider=video_provider,
                    video_model=model,
                    fallbacks=[],  # the SDK chain is not used; see the docstring
                    duration=duration,
                ).arun(sink=sink_, raise_on_failure=False, timeout=timeout)
                candidate = read_result(prompt.block, result, requested_video_model=model)
                clip_uri, clip_sha, cost = (
                    candidate.clip_uri, candidate.clip_sha256, candidate.cost_usd,
                )
                block = candidate
                steps_tail = result.run.steps[-1]
                if candidate.still_uri:
                    still = Asset(
                        url=candidate.still_uri,
                        sha256=candidate.still_sha256,
                        media_type="image/png",
                    )
            else:
                # A still already exists and was already paid for. Re-animating it
                # keeps the retry cheap AND keeps the picture identical, so a
                # provider substitution changes the lineage without silently
                # changing how the block looks.
                retry = await video_only_pipeline(
                    prompt, still, video_provider=video_provider, model=model,
                    duration=duration,
                ).arun(sink=sink_, raise_on_failure=False, timeout=timeout)
                step = retry.run.steps[0]
                steps_tail = step
                clip_uri, clip_sha = _asset(step)
                cost = float(getattr(step, "cost_usd", None) or 0.0)
        except BlockError:
            raise
        except Exception as exc:  # noqa: BLE001 — a dead provider is data, not a crash
            # Preflight rejects an unknown slug by raising, even under
            # raise_on_failure=False. Letting that escape would abort the whole
            # run on the first bad model in a chain whose entire purpose is to
            # survive one.
            transient = _is_transient(exc)
            attempts.append({
                "model": model,
                "status": f"error: {type(exc).__name__}",
                "retryable": transient,
            })
            if transient and attempt_n < len(RETRY_DELAYS_S):
                continue
            break

        spent += cost
        attempts.append({
            "model": model,
            "status": "ready" if clip_uri else "failed",
            "cost_usd": round(cost, 4),
        })

        if not clip_uri and attempt_n < len(RETRY_DELAYS_S):
            # A step that came back failed rather than raising. Retry the same
            # model only if the failure looks like it might clear — a 404 for a
            # slug that does not exist will not, and the CS-5 run burned four
            # attempts and 23 seconds of backoff proving that to itself.
            step_error = getattr(steps_tail, "error", None) or getattr(
                steps_tail, "error_code", ""
            )
            if _is_transient(f"{step_error} {getattr(steps_tail, 'error_message', '')}"):
                continue
            break

        if clip_uri:
            return replace(
                block,
                clip_uri=clip_uri,
                clip_sha256=clip_sha,
                video_model=model,
                used_fallback=model != chain[0],
                # The whole chain, not just the leg that worked. A block that
                # burned a still and two failed calls before succeeding cost that
                # much, and a budget that only counts successes is not a budget.
                cost_usd=round(spent, 4),
                status="ready",
                note=None if model == chain[0]
                else f"primary {chain[0]} failed; completed on {model}",
                attempts=tuple(attempts),
            )
        break  # this model is exhausted; move down the chain

    tried = ", ".join(f"{a['model']} ({a['status']})" for a in attempts)
    return replace(
        block if block is not None else BlockResult(n=prompt.block),
        cost_usd=round(spent, 4),
        status="failed",
        note=f"no video provider completed this block — tried {tried}",
        attempts=tuple(attempts),
    )
