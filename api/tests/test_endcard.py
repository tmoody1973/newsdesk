"""End-card validation. Nothing here renders; ffprobe reads a fixture.

The end card is the first frame in a Newsdesk video that no model produced.
That makes validation a trust-boundary job rather than an editorial one: the
publisher owns the content, we own refusing anything that will not decode.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from newsdesk.endcard import (
    MAX_URL_CHARS,
    EndCard,
    EndCardError,
    probe_image,
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
