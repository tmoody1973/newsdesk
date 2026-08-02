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
import uuid
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


DELIVERY_W = 1080
DELIVERY_H = 1920

# The logo kit's paper and ink, not invented here. 816434d retuned the whole app
# onto the supplied mark: paper #f9f6ee, ink #353334, red #f2322f. A card mixing
# its own cream with the app's would read as a mistake rather than a choice —
# which is the exact reason that commit moved the app's red four degrees of hue.
DEFAULT_GROUND = "#f9f6ee"
DEFAULT_INK = "0x353334"


def render_card(
    image: Path,
    out: Path,
    *,
    url: str | None,
    ffmpeg: str,
    width: int = DELIVERY_W,
    height: int = DELIVERY_H,
    ground: str = DEFAULT_GROUND,
    font: str | None = None,
) -> Path:
    """A DURATION_S still: the logo centred on the kit's ground, URL beneath.

    Refuses on an unreadable image rather than rendering a blank card. The
    publisher must not learn from someone else that their brand did not ship.

    The URL reaches drawtext via `textfile=`, not an inlined `text='...'`.
    That wasn't the first attempt — inlining, even with escaping, was tried
    and looked fine until the actual frame was checked (see git history on
    this line for the escaping that didn't work): drawtext's value survives
    two separate rounds of backslash-unescaping before drawtext reads it, and
    a single-escaped apostrophe didn't error, it silently opened an
    unterminated quote and burned the *rest of the filter string*
    ("expansion=none:fontcolor=...:x=...:y=...") into the visible card as
    text — worse than a crash, because nothing signals the mistake.
    `textfile=` sidesteps the whole class of bug: only the *path* touches
    the filtergraph string (and we choose that path, so it's always plain
    hex), while the URL's actual bytes are read from disk untouched.
    """
    probe_image(image)  # raises EndCardError before anything is encoded

    logo_h = int(height * 0.22)
    chain = [
        f"[1:v]scale=-1:{logo_h}:force_original_aspect_ratio=decrease[logo]",
        f"[0:v][logo]overlay=(W-w)/2:(H-h)/2-{int(height * 0.04)}[withlogo]",
    ]
    last = "withlogo"
    url_textfile: Path | None = None
    if url:
        url_textfile = out.parent / f".endcard-url-{uuid.uuid4().hex}.txt"
        url_textfile.write_text(url, encoding="utf-8")
        draw = (
            f"[{last}]drawtext=textfile={url_textfile.resolve()}:expansion=none"
            f":fontcolor={DEFAULT_INK}:fontsize={int(height * 0.026)}"
            f":x=(w-text_w)/2:y=h/2+{int(height * 0.10)}"
        )
        if font:
            draw += f":fontfile='{font}'"
        chain.append(f"{draw}[out]")
        last = "out"

    cmd = [
        ffmpeg, "-y",
        "-f", "lavfi", "-t", str(DURATION_S),
        "-i", f"color=c={ground}:s={width}x{height}:r=30",
        "-loop", "1", "-t", str(DURATION_S), "-i", str(image),
        "-f", "lavfi", "-t", str(DURATION_S), "-i", "anullsrc=r=48000:cl=stereo",
        "-filter_complex", ";".join(chain),
        "-map", f"[{last}]", "-map", "2:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
        "-c:a", "aac", "-ar", "48000", "-ac", "2",
        "-t", str(DURATION_S), str(out),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if url_textfile is not None:
        url_textfile.unlink(missing_ok=True)
    if proc.returncode != 0 or not out.exists():
        raise EndCardError(f"end card render failed: {proc.stderr[-400:]}")
    return out


def append_card(video: Path, card: Path, out: Path, *, ffmpeg: str) -> Path:
    """Concat the card after the mastered video.

    Deliberately NOT done inside assembly's filtergraph. That file produced the
    0.0 LUFS defect and the ffmpeg-5.1 framelog failure, and it is the wrong
    file to open for a two-and-a-half second bumper. The trade is recorded in
    the plan: the bed still fades under the last narration and the card holds in
    silence, rather than the music resolving on the logo.
    """
    if not card.exists():
        raise EndCardError("the end card segment is missing; refusing to publish "
                           "a video the publisher believes is branded")
    listing = out.with_suffix(".concat.txt")
    listing.write_text(f"file '{video.resolve()}'\nfile '{card.resolve()}'\n")
    proc = subprocess.run(
        [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
         "-ar", "48000", "-ac", "2", str(out)],
        capture_output=True, text=True,
    )
    listing.unlink(missing_ok=True)
    if proc.returncode != 0 or not out.exists():
        raise EndCardError(f"end card concat failed: {proc.stderr[-400:]}")
    return out
