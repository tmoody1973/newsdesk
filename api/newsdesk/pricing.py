"""GMICloud pricing registration, so every run reports real cost.

Genblaze ships `pricing=None` on family spec templates **by design** — per-slug
rates are contract-specific, so the SDK makes callers register their own rather
than guessing. Registering them here is what makes `step.cost_usd` populate,
which in turn puts per-block cost into the manifest, the Parquet audit, and the
Receipt.

Rates below are the published SDK defaults from
`docs/reference/pricing-recipes.md`, snapshot **2026-05-04**. GMI pricing is
contract-specific — verify against the console before trusting a total.
"""

from __future__ import annotations

from genblaze_core.providers import PricingContext, PricingStrategy, per_unit

# USD per asset.
IMAGE_RATES = {
    "seedream-5.0-lite": 0.035,
    "gemini-2.5-flash-image": 0.039,
    "flux-kontext-pro": 0.05,
    "seededit-3-0-i2i-250628": 0.03,
    "reve-edit-20250915": 0.007,
    "reve-edit-fast-20251030": 0.007,
}

# USD per asset. seedance-2.0 is billed per second and lives in SECOND_RATES.
VIDEO_FLAT_RATES = {
    "seedance-1-0-pro-250528": 0.30,
    # Dated slug. The undated "seedance-1-0-pro-fast" 404s at submit, so a rate
    # registered under that name would never have matched a real call and
    # cost_usd would have stayed None while looking configured.
    "seedance-1-0-pro-fast-251015": 0.022,
    "kling-image2video-v2.1-master": 0.28,
    "kling-image2video-v1.6-pro": 0.098,
}

# USD per second of output.
VIDEO_SECOND_RATES = {
    "seedance-2-0-260128": 0.052,
    # UNVERIFIED against the console — from GMI's own pricing post, which quotes
    # ~$0.09/s for Seedance 2.0 Fast. Registered because the alternative is
    # worse: with no rate at all, cost_usd comes back None and a run that used
    # this model reports as if the video were free. The CS-5 run on 2026-07-28
    # did exactly that, billing two blocks at $0.039 when only the image was
    # counted. A wrong number that is visibly wrong beats a silent zero.
    "seedance-2-0-fast-260128": 0.09,
}

# USD per asset.
AUDIO_RATES = {
    "ElevenLabs-TTS-v3": 0.10,
    "MiniMax-TTS-Speech-2.6-Turbo": 0.06,
}


def per_duration(rate: float) -> PricingStrategy:
    """Per-second strategy reading ``duration`` off the step.

    `ctx.params` does not exist — PricingContext carries (step, assets,
    provider_payload). The original read raised AttributeError inside the
    pricing hook, where genblaze swallows it, so every per-second model silently
    priced at None while looking configured. Found on the CS-5 run, which
    reported two seedance-2.0 blocks at $0.039 — the image alone.
    """

    def _strategy(ctx: PricingContext) -> float | None:
        params = getattr(ctx.step, "params", None) or {}
        duration = params.get("duration") or (ctx.provider_payload or {}).get("duration")
        return None if duration is None else float(duration) * rate

    return _strategy


def register_all(*, image=None, video=None, audio=None) -> None:
    """Attach rates to whichever providers are supplied.

    Call once at pipeline construction. Providers not passed are skipped, so a
    policy-gate-only run never touches this.
    """
    if image is not None:
        for slug, rate in IMAGE_RATES.items():
            image.models.register_pricing(slug, per_unit(rate))
    if video is not None:
        for slug, rate in VIDEO_FLAT_RATES.items():
            video.models.register_pricing(slug, per_unit(rate))
        for slug, rate in VIDEO_SECOND_RATES.items():
            video.models.register_pricing(slug, per_duration(rate))
    if audio is not None:
        for slug, rate in AUDIO_RATES.items():
            audio.models.register_pricing(slug, per_unit(rate))


def estimate_run(blocks: int = 6, *, seconds: int = 10, video_model: str) -> float:
    """Projected USD for one full story, for the budget guard and the README."""
    # gemini, not seedream: seedream silently ignores aspect_ratio and returns
    # square, so it is not a model this pipeline can actually use.
    image = IMAGE_RATES["gemini-2.5-flash-image"] * blocks
    if video_model in VIDEO_SECOND_RATES:
        video = VIDEO_SECOND_RATES[video_model] * seconds * blocks
    else:
        video = VIDEO_FLAT_RATES[video_model] * blocks
    audio = AUDIO_RATES["ElevenLabs-TTS-v3"] * blocks
    return round(image + video + audio, 2)
