#!/usr/bin/env python3
"""Prove the published kit is the one a run would actually use (MOO-425).

    uv run python scripts/verify_brand_kit.py
    uv run python scripts/verify_brand_kit.py --kit diorama

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
import sys
import tempfile
from pathlib import Path

from newsdesk import brandkit
from newsdesk.blockprompt import HOUSE_KIT, KNOWN_KITS
from newsdesk.config import BUCKETS, ConfigError


def main() -> int:
    kit_id = HOUSE_KIT
    if "--kit" in sys.argv:
        kit_id = sys.argv[sys.argv.index("--kit") + 1]
        if kit_id not in KNOWN_KITS:
            raise SystemExit(
                f"unknown kit '{kit_id}'. Choose from: {', '.join(KNOWN_KITS)}"
            )
    prefix = brandkit.kit_prefix(kit_id)

    try:
        kit = brandkit.load(kit_id=kit_id)
    except (brandkit.BrandKitError, ConfigError) as exc:
        print(f"FAIL  1. load from B2\n      {exc}")
        return 1

    print(f"OK    1. loaded from B2  ({prefix})")
    print(f"        negative      {kit.negative[:56]}…")
    print(f"        style tokens  {kit.style_tokens[:56]}…")
    print(f"        through-lines {len(kit.through_lines.get('through_lines', ()))} options")
    print(f"        voice         {kit.voice['primary']['voice_name']} "
          f"({kit.voice['primary']['model']})")
    print(f"        subtitles     {len(kit.subtitle_ass.splitlines())} lines")
    print(f"        style key     {kit.style_key_url or 'not published'}")

    with tempfile.TemporaryDirectory() as tmp:
        cache = brandkit.sync_down(Path(tmp) / "kit", kit_id=kit_id)
        os.environ["NEWSDESK_BRAND_KIT_DIR"] = str(cache)

        # Imported only now: blockprompt caches per directory, and importing it
        # before the env var is set would prove nothing about the published kit.
        from newsdesk.blockprompt import BlockPrompt, negative_line, platform_floor

        prompt = BlockPrompt.build(
            1,
            scene="A broadcast tower as a torn-paper cutout on cream card, taped at "
                  "one corner, with hand-drawn marker rings radiating from its mast.",
            motion="Rings contract inward; the outermost breaks apart.",
            audio="Room tone, one tape-peel.",
            kit=kit_id,
        )
        rendered = prompt.render()

        if kit.style_tokens not in rendered:
            print("FAIL  2. rendered prompt does not carry the published style tokens")
            return 1
        print(f"OK    2. prompt rendered from the published kit ({len(rendered)} chars)")

        # `kit.negative` is this kit's ADDITIONS — one of the six files. The
        # emitted NEGATIVE is the floor plus those additions, which is what POL-2
        # checks and what the provider receives. Comparing the two directly, as
        # this script did before the constant was split, reports drift on a kit
        # that is published correctly.
        expected = f"{platform_floor()}, {kit.negative}" if kit.negative else platform_floor()
        if negative_line(kit_id) != expected or not prompt.negative_is_intact:
            print("FAIL  3. POL-2 — the exclusion line differs from what is published")
            print(f"        composed  {negative_line(kit_id)!r}")
            print(f"        published {expected!r}")
            return 1
        print("OK    3. POL-2 holds against the published exclusion line")
        print(f"        floor     {platform_floor()}")
        print(f"        + {kit_id:8}  {kit.negative or '(no additions)'}")

    class _Empty:
        """A bucket with nothing in it."""

        def get(self, key: str) -> bytes:
            raise FileNotFoundError(key)

        def exists(self, key: str) -> bool:
            return False

    try:
        brandkit.load(store=_Empty(), kit_id=kit_id)
    except brandkit.BrandKitError as exc:
        first = str(exc).splitlines()[0]
        print(f"OK    4. a missing kit raises rather than defaulting\n        {first}")
    else:
        print("FAIL  4. a missing kit did NOT raise — the loader is falling back")
        return 1

    print(f"\nb2://{BUCKETS['brand_kit']}/{prefix} verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
