"""End-card validation. Nothing here renders; ffprobe reads a fixture.

The end card is the first frame in a Newsdesk video that no model produced.
That makes validation a trust-boundary job rather than an editorial one: the
publisher owns the content, we own refusing anything that will not decode.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from newsdesk.endcard import (
    DURATION_S,
    MAX_URL_CHARS,
    EndCard,
    EndCardError,
    append_card,
    probe_image,
    render_card,
    validate_url,
)

# A 1x1 PNG, base64 rather than hex so the literal survives line wrapping.
# Smallest thing ffprobe will agree is an image.
import base64

_PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8"
    "z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


@pytest.fixture
def png(tmp_path: Path) -> Path:
    p = tmp_path / "logo.png"
    p.write_bytes(_PNG_1X1)
    return p


def test_a_real_image_reports_its_dimensions(png: Path):
    assert probe_image(png) == (1, 1)


def test_a_file_that_is_not_an_image_is_refused(tmp_path: Path):
    bad = tmp_path / "logo.png"
    bad.write_bytes(b"this is not a png")
    with pytest.raises(EndCardError, match="not an image"):
        probe_image(bad)


def test_a_missing_file_is_refused(tmp_path: Path):
    with pytest.raises(EndCardError, match="not an image"):
        probe_image(tmp_path / "absent.png")


@pytest.mark.parametrize("raw,expected", [
    ("radiomilwaukee.org", "radiomilwaukee.org"),
    ("https://radiomilwaukee.org", "radiomilwaukee.org"),
    ("https://radiomilwaukee.org/", "radiomilwaukee.org"),
    ("  radiomilwaukee.org  ", "radiomilwaukee.org"),
])
def test_a_url_is_normalised_to_what_a_viewer_should_read(raw, expected):
    """The card shows a domain, not a protocol. Nobody types https:// off a video."""
    assert validate_url(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", "not a url at all", "x" * (MAX_URL_CHARS + 1)])
def test_an_unusable_url_is_refused(raw):
    with pytest.raises(EndCardError):
        validate_url(raw)


def test_an_end_card_records_that_no_model_made_it():
    card = EndCard(image_uri="b2://runs/x/endcard.png", url="radiomilwaukee.org",
                   supplied_by="Tarik Moody")
    assert card.manifest_entry()["generated"] is False
    assert card.manifest_entry()["supplied_by"] == "Tarik Moody"


def test_a_rendered_card_is_the_bed_fade_long(png: Path, tmp_path: Path):
    """2.5s, because that is what the music already fades over."""
    from newsdesk.assembly import probe_duration, resolve_ffmpeg
    out = tmp_path / "card.mp4"
    render_card(png, out, url="radiomilwaukee.org", ffmpeg=resolve_ffmpeg(needs_subtitles=False))
    assert out.exists()
    assert abs(probe_duration(out) - DURATION_S) < 0.15


def test_a_rendered_card_is_the_delivery_size(png: Path, tmp_path: Path):
    from newsdesk.assembly import resolve_ffmpeg
    out = tmp_path / "card.mp4"
    render_card(png, out, url="radiomilwaukee.org", ffmpeg=resolve_ffmpeg(needs_subtitles=False))
    assert probe_image(out) == (1080, 1920)


def test_appending_extends_the_video_by_the_card(png: Path, tmp_path: Path):
    from newsdesk.assembly import probe_duration, resolve_ffmpeg
    ff = resolve_ffmpeg(needs_subtitles=False)
    card = tmp_path / "card.mp4"
    render_card(png, card, url="radiomilwaukee.org", ffmpeg=ff)
    body = tmp_path / "body.mp4"
    render_card(png, body, url="radiomilwaukee.org", ffmpeg=ff)  # stand-in body
    out = tmp_path / "final.mp4"
    append_card(body, card, out, ffmpeg=ff)
    assert abs(probe_duration(out) - (DURATION_S * 2)) < 0.3


def test_a_missing_card_refuses_rather_than_rendering_without_it(tmp_path: Path):
    """A silently dropped end card means a publisher believes their brand shipped
    on a video where it did not, and hears about it from someone else."""
    from newsdesk.assembly import resolve_ffmpeg
    with pytest.raises(EndCardError, match="not an image"):
        render_card(tmp_path / "absent.png", tmp_path / "card.mp4",
                    url="x.org", ffmpeg=resolve_ffmpeg(needs_subtitles=False))


def test_appending_a_missing_card_refuses_rather_than_publishing_without_it(
    png: Path, tmp_path: Path
):
    """append_card's own guard: the brief's other missing-card test only exercises
    render_card. Nothing in the brief exercised append_card's `card.exists()`
    check, so it was implemented but unverified — the exact publisher-facing
    risk the docstring names, left untested."""
    from newsdesk.assembly import resolve_ffmpeg
    ff = resolve_ffmpeg(needs_subtitles=False)
    body = tmp_path / "body.mp4"
    render_card(png, body, url="radiomilwaukee.org", ffmpeg=ff)
    with pytest.raises(EndCardError, match="missing"):
        append_card(body, tmp_path / "absent-card.mp4", tmp_path / "final.mp4", ffmpeg=ff)


def test_a_url_that_would_break_out_of_the_drawtext_quoting_still_renders(
    png: Path, tmp_path: Path
):
    """validate_url's domain regex allows an unrestricted path segment
    (`\\S*`), so a caller that skips validate_url (or a URL with a quote in
    its path) can hand render_card a value that breaks drawtext's quoting.
    A crash here is a silently-missing end card, which is exactly what this
    module exists to refuse."""
    from newsdesk.assembly import resolve_ffmpeg
    out = tmp_path / "card.mp4"
    render_card(png, out, url="radiomilwaukee.org/it's:here",
                ffmpeg=resolve_ffmpeg(needs_subtitles=False))
    assert out.exists()
