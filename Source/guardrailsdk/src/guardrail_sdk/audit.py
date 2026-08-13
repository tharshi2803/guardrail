"""Structured JSONL audit logger for the Guardrail SDK."""

from __future__ import annotations

import json
import time
from pathlib import Path


class AuditLogger:
    """Append structured audit events as JSON lines."""

    def __init__(self, log_path: str = "guard_audit.jsonl") -> None:
        self._path = Path(log_path)

    def log(self, event: dict) -> None:
        """Write a single audit event with a timestamp."""
        event["ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with open(self._path, "a") as f:
            f.write(json.dumps(event) + "\n")
