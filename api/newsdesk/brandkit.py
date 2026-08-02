"""The published brand kit, read from B2 at runtime (MOO-425).

B2 use #2 of five. The kit that governs a run is the one published to
`b2://newsdesk-brand-kit/kit/`, not the one that happens to sit beside the
code — otherwise a deployed run styles itself off an unreviewed working copy
and the manifest's claim about what house style produced the video is a guess.

**This module fails loudly and never falls back.** A missing kit object raises
rather than substituting a bundled default, because a run that quietly used an
unpublished style is worse than a run that did not happen: the video ships, the
receipt says it followed the brand kit, and nothing in the record shows it
didn't.

`newsdesk/blockprompt.py` deliberately does not import this module. gate.py
imports blockprompt, and `tests/test_structure.py` fails the build if the
gate's transitive imports can reach a provider. The two meet at a directory
path instead: `sync_down()` materializes the fetched kit locally and
`blockprompt.kit_dir()` reads NEWSDESK_BRAND_KIT_DIR.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from newsdesk.blockprompt import HOUSE_KIT
from newsdesk.config import BUCKETS, backend

# Everything under one prefix so the kit is separable from the candidate
# renders and voice takes that share the bucket. The house kit keeps this bare
# prefix so nothing already published has to move. B2 keys are flat, so
# "kit/negative.txt" and "kit/diorama/negative.txt" are different keys with no
# collision and no migration.
KIT_PREFIX = "kit/"


def kit_prefix(kit_id: str | None) -> str:
    """The B2 prefix for one keyed kit. `None` and `"house"` are the same kit."""
    if not kit_id or kit_id == HOUSE_KIT:
        return KIT_PREFIX
    return f"{KIT_PREFIX}{kit_id}/"


# Absent any one of these, the kit is not a kit. Ordered as an editor would
# think about them: what is forbidden, what the house looks like, why, the
# art-direction menu, who reads it, how it is captioned.
REQUIRED_TEXT = (
    "negative.txt",
    "style-tokens.txt",
    "scene-guidance.txt",
    "through-lines.yaml",
    "voice.json",
    "subtitle.ass",
)

# Documentation, not a pipeline input. MOO-424 established that passing a
# style key as an image reference made consistency *worse* — two scenes off one
# key produced a blue ground and a tan ground, while naming the palette in text
# locked it. The Brand Kit page shows this image to an editor; no generation
# call receives it.
STYLE_KEY = "style-key.png"


class BrandKitError(RuntimeError):
    """Raised when the published kit is missing or unreadable.

    Never caught internally to substitute a default. See the module docstring.
    """


@dataclass(frozen=True)
class BrandKit:
    """The published kit, parsed. Immutable — a run cannot edit its own style."""

    negative: str
    style_tokens: str
    scene_guidance: str
    through_lines: dict[str, Any]
    voice: dict[str, Any]
    subtitle_ass: str
    style_key_url: str | None = None


def _fetch(store: Any, name: str, *, prefix: str = KIT_PREFIX) -> bytes:
    """One kit object, or a raise that names the exact key that is missing."""
    key = f"{prefix}{name}"
    try:
        data = store.get(key)
    except Exception as exc:  # noqa: BLE001 — every failure here is the same failure
        raise BrandKitError(
            f"brand kit incomplete: b2://{BUCKETS['brand_kit']}/{key} could not be read "
            f"({type(exc).__name__}: {exc}). Publish it with "
            f"`uv run python scripts/sync_brand_kit.py`. Refusing to fall back to a "
            f"local default — a run styled by an unpublished kit is worse than no run."
        ) from exc
    if not data:
        raise BrandKitError(
            f"brand kit incomplete: b2://{BUCKETS['brand_kit']}/{key} is empty."
        )
    return data


def load(*, store: Any | None = None, kit_id: str = HOUSE_KIT) -> BrandKit:
    """Fetch and parse one keyed kit. Raises unless every part is present."""
    store = store if store is not None else backend(BUCKETS["brand_kit"])
    prefix = kit_prefix(kit_id)

    raw = {name: _fetch(store, name, prefix=prefix).decode("utf-8") for name in REQUIRED_TEXT}

    try:
        through_lines = yaml.safe_load(raw["through-lines.yaml"]) or {}
        voice = json.loads(raw["voice.json"])
    except (yaml.YAMLError, json.JSONDecodeError) as exc:
        raise BrandKitError(f"published kit is malformed: {type(exc).__name__}: {exc}") from exc

    # The style key is documentation, so its absence is survivable — but it is
    # reported as None rather than as a working URL to something that isn't there.
    style_key_url: str | None = None
    key = f"{prefix}{STYLE_KEY}"
    try:
        if store.exists(key):
            style_key_url = store.get_durable_url(key)
    except Exception:  # noqa: BLE001 — a missing visual must not fail a run
        style_key_url = None

    return BrandKit(
        negative=raw["negative.txt"].strip(),
        style_tokens=raw["style-tokens.txt"].strip(),
        scene_guidance=raw["scene-guidance.txt"],
        through_lines=through_lines,
        voice=voice,
        subtitle_ass=raw["subtitle.ass"],
        style_key_url=style_key_url,
    )


def sync_down(dest: Path, *, store: Any | None = None) -> Path:
    """Materialize the published kit into `dest` and return it.

    Point NEWSDESK_BRAND_KIT_DIR at the result and `blockprompt` — and through
    it POL-2's byte comparison — reads the published kit rather than the
    working copy, without either module importing a network package.
    """
    store = store if store is not None else backend(BUCKETS["brand_kit"])
    dest.mkdir(parents=True, exist_ok=True)
    for name in REQUIRED_TEXT:
        (dest / name).write_bytes(_fetch(store, name))
    return dest
