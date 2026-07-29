"""The worker's HTTP surface (MOO-435).

The walls have to hold at the edge, not only in the CLI. A story posted from a
browser reaches the same parser a story on disk does, and a run that will end in
a refusal is refused at the door rather than five minutes and several dollars
later.

No network and no server socket: the handler's decision logic is exercised
directly, because what is worth testing here is which requests are turned away
and why.
"""

from __future__ import annotations

import pytest

from newsdesk import server
from newsdesk.storyfile import StoryFileError, parse_story

GOOD_STORY = {
    "id": "probe",
    "title": "A title",
    "through_line": "record",
    "facts": [{"text": "A sourced fact", "sources": ["https://example.org/a"]}],
}


@pytest.fixture(autouse=True)
def _clear_slots():
    server._running.clear()
    yield
    server._running.clear()


# --- Wall 1, at the edge -----------------------------------------------------


def test_a_posted_story_meets_the_same_parser_as_one_on_disk():
    """Not a looser check because it arrived over HTTP. The browser is the least
    trusted input this system has."""
    sf = parse_story(GOOD_STORY, where="posted story")
    assert sf.run_id == "probe"


def test_an_unsourced_posted_fact_is_refused_and_named():
    doc = {**GOOD_STORY, "facts": [{"text": "Turnout hit a record high", "sources": []}]}
    with pytest.raises(StoryFileError, match="Turnout hit a record high"):
        parse_story(doc, where="posted story")


# --- capacity ----------------------------------------------------------------


def test_a_second_run_of_the_same_story_is_refused():
    """Two runs of one story share a B2 prefix and a RunState key, so the second
    would overwrite the first one's state mid-flight."""
    server._claim_slot("cs2")
    with pytest.raises(server.RunRejected) as caught:
        server._claim_slot("cs2")
    assert caught.value.status == 409


def test_capacity_is_bounded_and_says_so():
    """A container that accepts a run it has no CPU for is lying to whoever
    started it. The Run Board would poll a state that never advances."""
    for i in range(server.MAX_CONCURRENT_RUNS):
        server._claim_slot(f"story-{i}")
    with pytest.raises(server.RunRejected) as caught:
        server._claim_slot("one-too-many")
    assert caught.value.status == 503


def test_a_finished_run_frees_its_slot():
    server._claim_slot("cs2")
    server._release("cs2")
    server._claim_slot("cs2")  # must not raise


# --- health ------------------------------------------------------------------


def test_health_reports_the_two_silent_failures():
    """ffmpeg without libass renders a caption-free video and exits 0; a missing
    Anton falls back to another face without a word. Both are invisible at
    runtime, so the container reports them at boot instead."""
    health = server._health()
    assert set(health) >= {
        "ok", "subtitles_filter", "anton_installed", "access_code_required",
    }
    assert health["ok"] is (health["subtitles_filter"] and health["anton_installed"])


def test_health_says_whether_the_access_code_is_set(monkeypatch):
    """A deploy that forgot the code is a public URL spending the GMI balance.
    It has to be visible without reading the container's environment."""
    monkeypatch.setattr(server, "ACCESS_CODE", "")
    assert server._health()["access_code_required"] is False
    monkeypatch.setattr(server, "ACCESS_CODE", "secret")
    assert server._health()["access_code_required"] is True
