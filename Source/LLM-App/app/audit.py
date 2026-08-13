"""Structured JSONL audit logger."""

from __future__ import annotations

import json
import time
from pathlib import Path

import structlog

_LOG_PATH = Path("audit.jsonl")
_logger = structlog.get_logger("audit")


def log_event(
    *,
    session_id: str | None = None,
    stage: str = "unknown",
    action: str = "allow",
    reason_code: str | None = None,
    layer: str | None = None,
    severity: str | None = None,
    scores: dict[str, float] | None = None,
    latency_ms: float = 0.0,
    rules_version: str | None = None,
    input_hash: str | None = None,
) -> None:
    """Append a single audit event as a JSON line."""
    event = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "session_id": session_id,
        "stage": stage,
        "action": action,
        "reason_code": reason_code,
        "layer": layer,
        "severity": severity,
        "scores": scores or {},
        "latency_ms": round(latency_ms, 2),
        "rules_version": rules_version,
        "input_hash": input_hash,
    }
    with open(_LOG_PATH, "a") as f:
        f.write(json.dumps(event) + "\n")
    _logger.info("audit_event", **event)
