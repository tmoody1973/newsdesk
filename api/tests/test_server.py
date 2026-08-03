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

import json

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


# --- /ingest, at the edge (task-1-brief, PLAN.md §B4) ------------------------


def test_ingest_body_must_be_json():
    with pytest.raises(json.JSONDecodeError):
        server._parse_body(b"not json")


def test_ingest_missing_url_is_refused():
    with pytest.raises(server.IngestRejected) as caught:
        server._validate_ingest_url(None)
    assert caught.value.status == 422


def test_ingest_blank_url_is_refused():
    with pytest.raises(server.IngestRejected) as caught:
        server._validate_ingest_url("   ")
    assert caught.value.status == 422


def test_ingest_refuses_a_non_http_scheme():
    """`file://` is a request to read the container's own disk, not a story."""
    with pytest.raises(server.IngestRejected) as caught:
        server._validate_ingest_url("file:///etc/passwd")
    assert caught.value.status == 422
    assert "scheme" in str(caught.value).lower()


def test_ingest_refuses_http_with_an_https_suggestion():
    """Our own gate, not genblaze's — the message names the fix a journalist
    can actually take, rather than surfacing check_ssrf's internal wording
    ("Only HTTPS URLs are allowed, got: http://")."""
    with pytest.raises(server.IngestRejected) as caught:
        server._validate_ingest_url("http://example.org/a-story")
    assert caught.value.status == 422
    assert "https://" in str(caught.value)


def test_ingest_refuses_a_private_ip_literal_without_opening_a_socket():
    """A private/loopback IP literal over https:// reaches `check_ssrf`'s
    actual IP blocklist (`resolve_ssrf`'s "Private/loopback URLs are not
    allowed") rather than tripping its earlier, unrelated HTTPS-only scheme
    check the way a plain http:// literal would. `getaddrinfo` on a literal
    IP is numeric parsing, not a DNS lookup — no socket opens, no network
    needed, still $0 and CI-safe."""
    with pytest.raises(server.IngestRejected) as caught:
        server._validate_ingest_url("https://169.254.169.254/")
    assert caught.value.status == 422


def test_ingest_accepts_a_plausible_https_url():
    assert server._validate_ingest_url("https://example.org/a-story") == (
        "https://example.org/a-story"
    )


def _sent(status, payload):
    """Drive Handler._send without a socket; return (headers, body)."""
    import io

    h = object.__new__(server.Handler)
    h.wfile = io.BytesIO()
    headers: list[tuple[str, str]] = []
    h.send_response = lambda s: None
    h.send_header = lambda k, v: headers.append((k, v))
    h.end_headers = lambda: None
    server.Handler._send(h, status, payload)
    return dict(headers), h.wfile.getvalue()


def test_a_204_carries_no_body_and_no_content_length():
    """RFC 9110 §15.3.5. Fly's HTTP/2 edge rejects a 204 with Content-Length
    as a malformed frame, which killed every browser CORS preflight — the
    wizard's POSTs died as 'network connection was lost'."""
    headers, body = _sent(204, {})
    assert body == b""
    assert "Content-Length" not in headers
    assert headers["Access-Control-Allow-Origin"] == "*"


def test_a_200_still_carries_its_json_and_cors_headers():
    headers, body = _sent(200, {"ok": True})
    assert body == b'{"ok": true}'
    assert headers["Content-Length"] == str(len(body))
    assert headers["Access-Control-Allow-Origin"] == "*"
