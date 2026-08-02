"""Kit resolution. B2 keys are flat, so kit/ and kit/diorama/ coexist and the
existing kit never moves — the cheapest correct answer, and no migration.
"""
from __future__ import annotations

import pytest

from newsdesk.blockprompt import negative_line, platform_floor
from newsdesk.brandkit import kit_prefix
from newsdesk.storyfile import StoryFileError, parse_story

_STORY = {
    "id": "kit-test",
    "title": "A story",
    "through_line": "fuse",
    "facts": [{"text": "A fact with a number, 5", "sources": [{"url": "https://x.org/a"}]}],
}


@pytest.mark.parametrize("kit_id,expected", [
    (None, "kit/"),
    ("house", "kit/"),
    ("diorama", "kit/diorama/"),
])
def test_the_house_kit_keeps_its_prefix_so_nothing_migrates(kit_id, expected):
    assert kit_prefix(kit_id) == expected


def test_a_story_defaults_to_the_house_kit():
    assert parse_story(dict(_STORY)).kit == "house"


def test_a_story_may_name_a_kit():
    assert parse_story({**_STORY, "kit": "diorama"}).kit == "diorama"


def test_an_unknown_kit_is_refused_at_wall_1():
    """422 at the door, no run created, nothing spent — a fact with no source's
    standard, applied to art direction."""
    with pytest.raises(StoryFileError, match="kit"):
        parse_story({**_STORY, "kit": "not-a-kit"})


FLOOR_TERMS = ("photorealism", "live-action footage", "3D render",
               "lip-sync", "talking characters", "watermark", "logo")
TEXT_TERMS = ("readable text", "letters", "words", "numbers", "captions", "subtitles")


@pytest.mark.parametrize("term", FLOOR_TERMS)
def test_the_floor_carries_every_harm_pol1_and_pol3_exist_for(term):
    assert term in platform_floor()


@pytest.mark.parametrize("term", TEXT_TERMS)
def test_the_text_default_is_not_in_the_floor(term):
    """The text half is narrowable. If it were in the floor, no kit could ever
    carry a letterpress label, which is the diorama style's whole signature."""
    assert term not in platform_floor()


def test_the_house_negative_still_forbids_text():
    """Narrowable is not narrowed. The house kit is unchanged in effect."""
    line = negative_line("house")
    for term in TEXT_TERMS:
        assert term in line


def test_every_kit_negative_starts_with_the_floor():
    """The whole POL-2 argument. Without it a kit is compared against itself."""
    for kit_id in ("house", "diorama"):
        assert negative_line(kit_id).startswith(platform_floor())
