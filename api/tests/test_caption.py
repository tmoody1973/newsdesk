"""Caption generation and the checks that run before any model output is trusted.

Every test injects a fake chat_fn or builds a Caption by hand. Nothing here
reaches a provider, so the suite stays at $0 with no network.
"""
from __future__ import annotations

import pytest
from fixtures import cs1_story

from newsdesk.caption import (
    HOOK_LIMIT,
    Caption,
    caption_problems,
    sources_for,
)


def _caption(**over) -> Caption:
    base = dict(
        platform="youtube",
        variant=1,
        hook="Milwaukee has sixty-five thousand lead pipes and a 2037 deadline.",
        body="The city replaced roughly three thousand three hundred lines in 2025.",
        cta="Subscribe for more data-driven explainers.",
        hashtags=("#Infrastructure", "#PublicHealth", "#Shorts"),
        sources=("https://dailyreporter.com/2026/05/06/",),
    )
    base.update(over)
    return Caption(**base)


def test_a_clean_youtube_caption_has_no_problems():
    assert caption_problems(_caption()) == ()


def test_a_hook_past_the_platform_limit_is_a_problem():
    """The hook is the search snippet. Past the limit it truncates mid-sentence."""
    long_hook = "x" * (HOOK_LIMIT["youtube"] + 1)
    problems = caption_problems(_caption(hook=long_hook))
    assert any("hook" in p for p in problems)


def test_youtube_without_the_shorts_tag_is_a_problem():
    """The guide is explicit: #Shorts signals categorisation to the algorithm."""
    problems = caption_problems(_caption(hashtags=("#A", "#B", "#C")))
    assert any("#Shorts" in p for p in problems)


def test_linkedin_does_not_require_the_shorts_tag():
    c = _caption(platform="linkedin", hashtags=("#A", "#B", "#C"))
    assert caption_problems(c) == ()


@pytest.mark.parametrize("tags", [("#A", "#B"), ("#A", "#B", "#C", "#D", "#E", "#F")])
def test_hashtag_count_outside_three_to_five_is_a_problem(tags):
    """The guide treats hashtags as category labels, not reach boosters."""
    problems = caption_problems(_caption(platform="linkedin", hashtags=tags))
    assert any("hashtag" in p for p in problems)


def test_shouting_is_a_problem():
    """All-caps and exclamation runs break the sepia aesthetic the guide protects."""
    assert any("caps" in p for p in caption_problems(_caption(body="THIS IS URGENT")))
    assert any("exclamation" in p for p in caption_problems(_caption(body="Wow!!")))


def test_emoji_are_a_problem():
    assert any("emoji" in p for p in caption_problems(_caption(body="Big news 🚨")))


def test_sources_come_from_the_story_verbatim():
    """A model must never write a citation. These are copied, not composed.

    Asserted against the fixture's own values rather than a shape test — a
    check that only asks "does it look like a URL" would pass on an invented
    one, which is the single thing this function exists to prevent.
    """
    story = cs1_story()
    expected = tuple(
        dict.fromkeys(s.value for f in story.facts for s in f.sources)
    )
    assert sources_for(story) == expected
    assert len(expected) == len(set(expected)), "deduped, order preserved"
