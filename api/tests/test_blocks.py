"""Failure classification and the fallback chain (MOO-424, CS-5).

The chain is walked by `blocks.run_block` rather than left to genblaze's
`fallback_models`, which fires only on ProviderErrorCode.MODEL_ERROR — a branch
its classifier reaches only for "not found" / "not available", and only after
auth and server checks have claimed anything containing 401, 403, 400, 500, 502
or 503. GMI says "model X does not exist" over HTTP 404, so it lands in UNKNOWN
and the chain never engages. Measured, not assumed.
"""

from __future__ import annotations

import pytest

from newsdesk.blocks import RETRY_DELAYS_S, _is_transient


@pytest.mark.parametrize(
    ("message", "retryable"),
    [
        # Worth trying the same model again.
        ("Backend error (401). Please try again.", True),
        ("GMICloud chat failed (429): rate_limit_exceeded", True),
        ("Service temporarily unavailable. All endpoints are overloaded.", True),
        ("GMICloud submit failed (500): server error", True),
        ("read operation timed out", True),
        ("Read timeout on endpoint", True),
        # No status code anywhere in it — genblaze's ElevenLabs adapter reports
        # a throttle as `code=rate_limit` and the 429 never reaches the message.
        ("ElevenLabs TTS failed: headers: {...} (code=rate_limit)", True),
        # Will never clear. Retrying only burns the backoff.
        ("GMICloud submit failed (404): model seedance-x does not exist", False),
        ("invalid input: duration must be 4-15", False),
    ],
)
def test_failure_classification(message, retryable):
    assert _is_transient(message) is retryable


def test_a_401_is_treated_as_retryable_on_purpose():
    """Wrong in general, right here.

    GMI wraps an upstream authorization failure as a 500 body, and the same key
    succeeds on the next call about half the time — ten raw submits to
    seedance-2-0-fast-260128 on 2026-07-28 returned five 200s and five 401s.
    Treating that as fatal abandons a working model and bills the fallback's
    higher rate for a failure that would have cleared. A genuinely revoked key
    still fails every attempt and still walks the chain; it just costs three
    tries first.
    """
    assert _is_transient("Backend error (401). Please try again.")


def test_the_backoff_is_bounded():
    """An unbounded retry on a flaky provider is an unbounded bill."""
    assert 1 <= len(RETRY_DELAYS_S) <= 5
    assert all(d > 0 for d in RETRY_DELAYS_S)
    assert list(RETRY_DELAYS_S) == sorted(RETRY_DELAYS_S), "backoff should widen"


# --- the image leg's chain (2026-07-28) --------------------------------------
#
# `run_block` has carried a retry for the video leg since MOO-424; the image leg
# had none, so one transient GMI read timeout failed that block outright at $0.
# A live six-block roll on gemini-3-pro-image-preview came back 4/6 for exactly
# that reason. These tests hold the two properties that cost us the two blocks:
# a timeout is retried on the SAME model, and a dead model still reaches the
# fallback rather than ending the run.


class _FakeStep:
    def __init__(self, url, cost, status="succeeded", error=""):
        self.assets = [type("A", (), {"url": url})()] if url else []
        self.cost_usd = cost
        self.status = status
        self.error = error


class _FakeImageProvider:
    """Replays a scripted sequence of outcomes and records the models asked for.

    Outcomes are (url_or_None, error_text). A None url with transient error text
    is what a GMI submit timeout looks like from inside the pipeline.
    """

    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.asked: list[str] = []

    def take(self, model):
        self.asked.append(model)
        return self.outcomes.pop(0) if self.outcomes else (None, "read timed out")


@pytest.fixture
def _no_sleep(monkeypatch):
    """The backoff is asserted separately; nobody should wait 23s for a unit test."""
    import newsdesk.blocks as blocks

    async def instant(_seconds):
        return None

    monkeypatch.setattr(blocks.asyncio, "sleep", instant)


def _patch_pipeline(monkeypatch, provider):
    """Replace the still pipeline with the fake, keeping run_still's own logic."""
    import newsdesk.blocks as blocks

    class _Pipe:
        def __init__(self, model):
            self.model = model

        async def arun(self, **_kwargs):
            url, error = provider.take(self.model)
            step = _FakeStep(url, 0.039 if url else 0.0, error=error)
            return type("R", (), {"run": type("Run", (), {"steps": [step]})()})()

    monkeypatch.setattr(
        blocks, "still_only_pipeline",
        lambda prompt, *, image_provider, model="": _Pipe(model or blocks.IMAGE_MODEL),
    )


def test_a_timed_out_still_is_retried_on_the_same_model(monkeypatch, _no_sleep):
    """The 4/6 defect. Two timeouts then success must stay on the primary."""
    import asyncio

    import newsdesk.blocks as blocks

    provider = _FakeImageProvider([
        (None, "GMICloud submit failed: The read operation timed out"),
        (None, "GMICloud submit failed: The read operation timed out"),
        ("https://b2/still.png", ""),
    ])
    _patch_pipeline(monkeypatch, provider)

    url, spent, used = asyncio.run(
        blocks.run_still(object(), image_provider=provider)
    )

    assert url == "https://b2/still.png"
    assert used == blocks.IMAGE_MODEL, "a timeout must not abandon a working model"
    assert provider.asked == [blocks.IMAGE_MODEL] * 3
    assert spent == pytest.approx(0.039), "failed attempts cost $0 and bill nothing"


def test_a_dead_image_model_reaches_the_fallback(monkeypatch, _no_sleep):
    """gemini-2.5-flash-image went down for a full day. 6/6 blocks, every attempt.

    A run must degrade to the lower-resolution fallback rather than produce
    nothing — the picture is worse, the video still exists.
    """
    import asyncio

    import newsdesk.blocks as blocks

    provider = _FakeImageProvider(
        [(None, "read operation timed out")] * (len(RETRY_DELAYS_S) + 1)
        + [("https://b2/fallback.png", "")]
    )
    _patch_pipeline(monkeypatch, provider)

    url, _spent, used = asyncio.run(
        blocks.run_still(object(), image_provider=provider)
    )

    assert url == "https://b2/fallback.png"
    assert used == blocks.IMAGE_FALLBACK
    assert provider.asked[0] == blocks.IMAGE_MODEL
    assert provider.asked[-1] == blocks.IMAGE_FALLBACK


def test_a_permanent_failure_does_not_burn_the_backoff(monkeypatch, _no_sleep):
    """"model does not exist" is a 404 and will never clear. One try, then move on."""
    import asyncio

    import newsdesk.blocks as blocks

    provider = _FakeImageProvider([
        (None, "GMICloud submit failed (404): model gemini-9 does not exist"),
        ("https://b2/fallback.png", ""),
    ])
    _patch_pipeline(monkeypatch, provider)

    url, _spent, used = asyncio.run(
        blocks.run_still(object(), image_provider=provider)
    )

    assert url == "https://b2/fallback.png"
    assert used == blocks.IMAGE_FALLBACK
    assert provider.asked == [blocks.IMAGE_MODEL, blocks.IMAGE_FALLBACK], (
        "a 404 should cost one attempt, not four"
    )
