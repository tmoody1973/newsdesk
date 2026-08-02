"""Kit resolution. B2 keys are flat, so kit/ and kit/diorama/ coexist and the
existing kit never moves — the cheapest correct answer, and no migration.
"""
from __future__ import annotations

import pytest

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
