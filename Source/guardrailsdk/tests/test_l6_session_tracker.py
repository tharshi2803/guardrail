"""Tests for L6 — Session tracker."""

import time

from guardrail_sdk.config import RateLimitConfig, SessionConfig
from guardrail_sdk.layers.l6_session_tracker import L6SessionTracker


def test_rate_limit_enforcement():
    """Exceeding RPM should trigger a block."""
    config = SessionConfig(rate_limit=RateLimitConfig(rpm=3, tpm=100000))
    tracker = L6SessionTracker(config)

    # First 3 should pass
    for _ in range(3):
        result = tracker.check_rate_limit("session-1")
        assert result is None

    # 4th should be blocked
    result = tracker.check_rate_limit("session-1")
    assert result is not None
    assert result.blocked is True
    assert result.reason_code == "rate_limit_rpm"


def test_suspicion_accumulation():
    """Suspicion score should increase on updates."""
    config = SessionConfig()
    tracker = L6SessionTracker(config)

    tracker.update_suspicion("session-1", 0.9)
    state = tracker.get_session_state("session-1")
    assert state["suspicion_score"] > 0.0

    tracker.update_suspicion("session-1", 0.9)
    state2 = tracker.get_session_state("session-1")
    assert state2["suspicion_score"] > state["suspicion_score"]


def test_suspicion_decay():
    """Suspicion score should decay over time."""
    config = SessionConfig(suspicion_decay_seconds=1)  # Fast decay for testing
    tracker = L6SessionTracker(config)

    tracker.update_suspicion("session-1", 1.0)
    state_before = tracker.get_session_state("session-1")

    # Simulate time passing
    tracker._sessions["session-1"].last_decay = time.time() - 2.0

    # Rate limit check triggers decay
    tracker.check_rate_limit("session-1")
    state_after = tracker.get_session_state("session-1")

    assert state_after["suspicion_score"] < state_before["suspicion_score"]
