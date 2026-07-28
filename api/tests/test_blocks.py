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
