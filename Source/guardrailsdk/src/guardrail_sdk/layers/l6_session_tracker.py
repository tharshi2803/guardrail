"""L6 — Session tracker layer.

Cross-cutting layer that tracks per-session rate limits and suspicion
scores. Uses an in-memory store (Redis stub).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from ..config import SessionConfig
from ..models import GuardResult


@dataclass
class SessionState:
    """Per-session tracking state."""

    request_timestamps: list[float] = field(default_factory=list)
    token_count: int = 0
    suspicion_score: float = 0.0
    last_decay: float = field(default_factory=time.time)


class L6SessionTracker:
    """In-memory session tracker with rate limiting and suspicion scoring."""

    def __init__(self, config: SessionConfig) -> None:
        self._config = config
        self._sessions: dict[str, SessionState] = {}

    def _get_session(self, session_id: str) -> SessionState:
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionState()
        return self._sessions[session_id]

    def check_rate_limit(self, session_id: str) -> GuardResult | None:
        """Check RPM rate limit. Returns blocked result if exceeded."""
        state = self._get_session(session_id)
        now = time.time()

        # Decay suspicion
        elapsed = now - state.last_decay
        if elapsed > 0 and self._config.suspicion_decay_seconds > 0:
            decay = (elapsed / self._config.suspicion_decay_seconds) * 0.1
            state.suspicion_score = max(0.0, state.suspicion_score - decay)
            state.last_decay = now

        # Sliding window: remove timestamps older than 60s
        window_start = now - 60.0
        state.request_timestamps = [
            ts for ts in state.request_timestamps if ts > window_start
        ]

        # Check RPM
        if len(state.request_timestamps) >= self._config.rate_limit.rpm:
            return GuardResult.blocked_result(
                reason_code="rate_limit_rpm",
                layer="L6_session_tracker",
                severity="medium",
                scores={"rpm": float(len(state.request_timestamps))},
            )

        # Record this request
        state.request_timestamps.append(now)
        state.request_count = len(state.request_timestamps)

        # Check suspicion hard-block
        if state.suspicion_score >= 0.9:
            return GuardResult.blocked_result(
                reason_code="suspicion_hard_block",
                layer="L6_session_tracker",
                severity="critical",
                scores={"suspicion_score": state.suspicion_score},
            )

        return None

    def update_suspicion(self, session_id: str, score: float) -> None:
        """Update suspicion score with weighted average."""
        state = self._get_session(session_id)
        # Weighted running average: new = old * 0.7 + score * 0.3
        state.suspicion_score = state.suspicion_score * 0.7 + score * 0.3

    def get_session_state(self, session_id: str) -> dict:
        """Return current session state as a dict."""
        state = self._get_session(session_id)
        return {
            "request_count": len(state.request_timestamps),
            "suspicion_score": round(state.suspicion_score, 4),
            "token_count": state.token_count,
        }
