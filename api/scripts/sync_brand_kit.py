#!/usr/bin/env python3
"""Publish one local brand kit to B2. Idempotent (MOO-425).

    uv run python scripts/sync_brand_kit.py                    # the house kit
    uv run python scripts/sync_brand_kit.py --kit diorama      # a keyed kit
    uv run python scripts/sync_brand_kit.py --check            # report drift, upload nothing

One kit per run, and the default is the house kit, byte for byte what it was
before kits were keyed. `--kit diorama` publishes `kit/diorama/` and touches no
house object — B2 keys are flat, so the two prefixes are unrelated keys and
nothing migrates.

Idempotence is decided on a SHA-256 we store as object metadata, not on the
ETag. B2 returns the MD5 for single-PUT objects and something opaque for
multipart ones, so an ETag comparison would silently re-upload the large files
on every run and quietly pass on the small ones — the worst of both.

`--check` is the one that matters for the acceptance criterion: it answers
"does what is published still match what is committed?" without changing
either. Run it before a demo.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

from newsdesk.blockprompt import HOUSE_KIT, KNOWN_KITS
from newsdesk.brandkit import FLOOR, KIT_PREFIX, REQUIRED_TEXT, STYLE_KEY, kit_prefix
from newsdesk.config import BUCKETS, ConfigError, backend

REPO_ROOT = Path(__file__).resolve().parents[2]
LOCAL_KIT = REPO_ROOT / "brand-kit"

CONTENT_TYPES = {
    ".txt": "text/plain; charset=utf-8",
    ".yaml": "application/yaml",
    ".json": "application/json",
    ".ass": "text/x-ssa; charset=utf-8",
    ".png": "image/png",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def published_digest(store, key: str) -> str | None:
    """The SHA-256 we recorded when we last published this key, if any."""
    try:
        meta = store.head(key)
    except Exception:  # noqa: BLE001 — absent or unreadable both mean "publish it"
        return None
    return meta.metadata.get("sha256") if meta else None


def _kit_id(argv: list[str]) -> str:
    if "--kit" not in argv:
        return HOUSE_KIT
    kit = argv[argv.index("--kit") + 1]
    if kit not in KNOWN_KITS:
        raise SystemExit(f"unknown kit '{kit}'. Choose from: {', '.join(KNOWN_KITS)}")
    return kit


def main() -> int:
    check_only = "--check" in sys.argv
    kit_id = _kit_id(sys.argv)
    prefix = kit_prefix(kit_id)
    local = LOCAL_KIT if kit_id == HOUSE_KIT else LOCAL_KIT / kit_id

    try:
        store = backend(BUCKETS["brand_kit"])
    except ConfigError as exc:
        print(f"FAIL  {exc}")
        return 1

    # The style key is optional — it is documentation, and it may not be picked
    # yet. Everything else is required, and a missing one is a failure here
    # rather than a surprise inside brandkit.load() during a run.
    #
    # The floor rides along with EVERY kit and always at the root prefix. It is
    # not part of any kit — no kit may narrow it — but `negative_line()` cannot
    # compose without it, so a kit published without it is a kit that cannot be
    # used. Its source is always the root directory, never the kit's own.
    names: list[tuple[str, Path, str]] = [(FLOOR, LOCAL_KIT / FLOOR, KIT_PREFIX)]
    names += [(name, local / name, prefix) for name in list(REQUIRED_TEXT) + [STYLE_KEY]]

    uploaded = unchanged = missing = drifted = 0

    for name, path, at in names:
        key = f"{at}{name}"

        if not path.exists():
            # Everything except the style key is required — including the floor,
            # whose absence is not a load failure but a gate failure, one layer
            # further in and after the run has started.
            if name != STYLE_KEY:
                print(f"  MISSING   {name}  — a run on this kit will refuse without it")
                missing += 1
            else:
                print(f"  skipped   {name}  — optional")
            continue

        data = path.read_bytes()
        digest = sha256(data)

        if published_digest(store, key) == digest:
            print(f"  unchanged {name}")
            unchanged += 1
            continue

        if check_only:
            print(f"  DRIFTED   {name}  — local differs from what is published")
            drifted += 1
            continue

        store.put(
            key,
            data,
            content_type=CONTENT_TYPES.get(path.suffix, "application/octet-stream"),
            metadata={"sha256": digest},
        )
        print(f"  uploaded  {name}  ({len(data):,} bytes)")
        uploaded += 1

    print(
        f"\nb2://{BUCKETS['brand_kit']}/{prefix}  kit '{kit_id}': "
        f"{uploaded} uploaded, {unchanged} unchanged"
        + (f", {drifted} drifted" if drifted else "")
        + (f", {missing} required file(s) missing" if missing else "")
    )

    if missing:
        return 1
    if check_only and drifted:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
