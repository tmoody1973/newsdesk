#!/usr/bin/env python3
"""Publish the local brand kit to B2. Idempotent (MOO-425).

    uv run python scripts/sync_brand_kit.py            # publish changed files
    uv run python scripts/sync_brand_kit.py --check    # report drift, upload nothing

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

from newsdesk.brandkit import KIT_PREFIX, REQUIRED_TEXT, STYLE_KEY
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


def main() -> int:
    check_only = "--check" in sys.argv

    try:
        store = backend(BUCKETS["brand_kit"])
    except ConfigError as exc:
        print(f"FAIL  {exc}")
        return 1

    # The style key is optional — it is documentation, and it may not be picked
    # yet. Everything else is required, and a missing one is a failure here
    # rather than a surprise inside brandkit.load() during a run.
    names = list(REQUIRED_TEXT) + [STYLE_KEY]

    uploaded = unchanged = missing = drifted = 0

    for name in names:
        path = LOCAL_KIT / name
        key = f"{KIT_PREFIX}{name}"

        if not path.exists():
            if name in REQUIRED_TEXT:
                print(f"  MISSING   {name}  — brandkit.load() will refuse without it")
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
        f"\nb2://{BUCKETS['brand_kit']}/{KIT_PREFIX}  "
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
