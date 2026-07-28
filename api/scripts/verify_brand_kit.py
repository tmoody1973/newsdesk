#!/usr/bin/env python3
"""Prove the published kit is the one a run would actually use (MOO-425).

    uv run python scripts/verify_brand_kit.py

Four checks, in the order the issue's verification checklist asks for them:

  1. The kit loads from B2 and parses.
  2. A block prompt renders from the *published* kit with the local kit
     unreadable — NEWSDESK_BRAND_KIT_DIR is pointed at a directory fetched from
     B2, never at the working copy.
  3. POL-2 holds against the published exclusion line, so the gate and the kit
     agree byte for byte.
  4. A missing kit raises instead of falling back. This is the one worth having:
     a loader that quietly defaults would pass checks 1-3 and still ship a video
     styled by something nobody published.

Reads only. Writes nothing to B2.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from newsdesk import brandkit
from newsdesk.config import BUCKETS, ConfigError


def main() -> int:
    try:
        kit = brandkit.load()
    except (brandkit.BrandKitError, ConfigError) as exc:
        print(f"FAIL  1. load from B2\n      {exc}")
        return 1

    print("OK    1. loaded from B2")
    print(f"        negative      {kit.negative[:56]}…")
    print(f"        style tokens  {kit.style_tokens[:56]}…")
    print(f"        through-lines {len(kit.through_lines.get('through_lines', ()))} options")
    print(f"        voice         {kit.voice['primary']['voice_name']} "
          f"({kit.voice['primary']['model']})")
    print(f"        subtitles     {len(kit.subtitle_ass.splitlines())} lines")
    print(f"        style key     {kit.style_key_url or 'not published'}")

    with tempfile.TemporaryDirectory() as tmp:
        cache = brandkit.sync_down(Path(tmp) / "kit")
        os.environ["NEWSDESK_BRAND_KIT_DIR"] = str(cache)

        # Imported only now: blockprompt caches per directory, and importing it
        # before the env var is set would prove nothing about the published kit.
        from newsdesk.blockprompt import BlockPrompt, negative_line

        prompt = BlockPrompt.build(
            1,
            scene="A broadcast tower as a torn-paper cutout on cream card, taped at "
                  "one corner, with hand-drawn marker rings radiating from its mast.",
            motion="Rings contract inward; the outermost breaks apart.",
            audio="Room tone, one tape-peel.",
        )
        rendered = prompt.render()

        if kit.style_tokens not in rendered:
            print("FAIL  2. rendered prompt does not carry the published style tokens")
            return 1
        print(f"OK    2. prompt rendered from the published kit ({len(rendered)} chars)")

        if negative_line() != kit.negative or not prompt.negative_is_intact:
            print("FAIL  3. POL-2 — the exclusion line differs from what is published")
            return 1
        print("OK    3. POL-2 holds against the published exclusion line")

    class _Empty:
        """A bucket with nothing in it."""

        def get(self, key: str) -> bytes:
            raise FileNotFoundError(key)

        def exists(self, key: str) -> bool:
            return False

    try:
        brandkit.load(store=_Empty())
    except brandkit.BrandKitError as exc:
        first = str(exc).splitlines()[0]
        print(f"OK    4. a missing kit raises rather than defaulting\n        {first}")
    else:
        print("FAIL  4. a missing kit did NOT raise — the loader is falling back")
        return 1

    print(f"\nb2://{BUCKETS['brand_kit']}/{brandkit.KIT_PREFIX} verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
