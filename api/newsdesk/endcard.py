"""The publisher's own mark, and the one frame no model made.

POL-1 and POL-4 govern generated frames. This one is composited: the URL is
drawn by ffmpeg from a string a human typed, so it cannot garble, and a garbled
word read as a misquote is the entire harm POL-4 names. Generated text and
composited text are different things — stated here once so it is not re-argued.

What we do owe is honesty in the record. The manifest says generated: false and
names the human who supplied it, because a receipt that accounts for every frame
except one is a receipt that misleads by omission.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# 2.5s, matching assembly.BED_FADE_OUT_S. Not a coincidence and not arbitrary:
# it is the length the bed already fades over, so the two agree by construction.
DURATION_S = 2.5

MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_EDGE = 4096
MAX_URL_CHARS = 100

_SCHEME_RE = re.compile(r"^[a-z][a-z0-9+.\-]*://", re.IGNORECASE)
_DOMAINISH_RE = re.compile(r"^[a-z0-9][a-z0-9.\-]*\.[a-z]{2,}(/\S*)?$", re.IGNORECASE)


class EndCardError(ValueError):
    """The supplied image or URL cannot be used. Refused at the door."""


@dataclass(frozen=True)
class EndCard:
    image_uri: str
    url: str | None
    supplied_by: str

    def manifest_entry(self) -> dict[str, Any]:
        return {
            "image": self.image_uri,
            "url": self.url,
            "supplied_by": self.supplied_by,
            "generated": False,
        }


def probe_image(path: Path) -> tuple[int, int]:
    """(width, height) from ffprobe. Measure, never infer — assembly's rule.

    ffprobe rather than a new dependency: assembly already requires it, and a
    header parser we wrote ourselves would be one more thing to be wrong about.
    """
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height",
         "-of", "csv=p=0:s=x", str(path)],
        capture_output=True, text=True,
    )
    try:
        width, height = (int(v) for v in proc.stdout.strip().split("x")[:2])
    except (ValueError, IndexError):
        raise EndCardError(f"{path.name} is not an image ffmpeg can read") from None
    # A file ffprobe can't parse as a stream still exits 0 and prints "0x0"
    # via csv=p=0:s=x instead of an empty row, so 0x0 unpacks and parses
    # cleanly above — it does not raise on its own. Zero is never a real
    # image's dimension, so it is the same refusal as an unparseable one.
    if width <= 0 or height <= 0:
        raise EndCardError(f"{path.name} is not an image ffmpeg can read")
    if width > MAX_IMAGE_EDGE or height > MAX_IMAGE_EDGE:
        raise EndCardError(
            f"{path.name} is {width}x{height}; the longest edge may be "
            f"{MAX_IMAGE_EDGE}px"
        )
    return width, height


def validate_bytes(data: bytes) -> None:
    if not data:
        raise EndCardError("the uploaded file is empty")
    if len(data) > MAX_IMAGE_BYTES:
        raise EndCardError(
            f"the image is {len(data) // 1024}KB; the limit is "
            f"{MAX_IMAGE_BYTES // 1024}KB"
        )


def validate_url(raw: str) -> str:
    """Normalise to the domain a viewer should read off the card.

    The protocol is dropped because nobody types https:// from a video, and a
    trailing slash reads as a typo at 1080x1920.
    """
    text = (raw or "").strip()
    if not text:
        raise EndCardError("the website is empty")
    if len(text) > MAX_URL_CHARS:
        raise EndCardError(
            f"the website is {len(text)} characters; the limit is {MAX_URL_CHARS}"
        )
    text = _SCHEME_RE.sub("", text).rstrip("/")
    if not _DOMAINISH_RE.match(text):
        raise EndCardError(f"{raw!r} does not look like a website address")
    return text
