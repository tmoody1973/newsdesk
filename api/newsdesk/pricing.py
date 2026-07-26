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
    "seedance-1-0-pro-fast": 0.022,
    "kling-image2video-v2.1-master": 0.28,
    "kling-image2video-v1.6-pro": 0.098,
}

# USD per second of output.
VIDEO_SECOND_RATES = {
    "seedance-2-0-260128": 0.052,
}

# USD per asset.
AUDIO_RATES = {
    "ElevenLabs-TTS-v3": 0.10,
    "MiniMax-TTS-Speech-2.6-Turbo": 0.06,
}


def per_duration(rate: float) -> PricingStrategy:
    """Per-second strategy reading ``duration`` from step params."""

    def _strategy(ctx: PricingContext) -> float | None:
        duration = ctx.params.get("duration")
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
    image = IMAGE_RATES["seedream-5.0-lite"] * blocks
    if video_model in VIDEO_SECOND_RATES:
        video = VIDEO_SECOND_RATES[video_model] * seconds * blocks
    else:
        video = VIDEO_FLAT_RATES[video_model] * blocks
    audio = AUDIO_RATES["ElevenLabs-TTS-v3"] * blocks
    return round(image + video + audio, 2)
