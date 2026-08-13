"""Core data models for the Guardrail SDK."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


class AttackLabel(str, Enum):
    """Known attack categories."""

    PROMPT_INJECTION = "prompt_injection"
    JAILBREAK_ROLEPLAY = "jailbreak_roleplay"
    HARMFUL_CONTENT = "harmful_content"
    PII_EXFIL = "pii_exfil"
    DOS = "dos"
    ENCODING_ATTACK = "encoding_attack"


@dataclass
class GuardContext:
    """Mutable state carried through the guard pipeline for a session."""

    canary_token: str = ""
    session_id: str = "default"
    system_prompt: str = ""
    request_count: int = 0
    suspicion_score: float = 0.0


@dataclass
class GuardResult:
    """Outcome of a guard check."""

    blocked: bool
    action: Literal["allow", "block", "quarantine", "slow"]
    reason_code: str | None = None
    layer: str | None = None
    severity: Literal["low", "medium", "high", "critical"] | None = None
    scores: dict[str, float] = field(default_factory=dict)
    latency_ms: float = 0.0
    rules_version: str = ""
    ctx: GuardContext | None = None
    sanitised_text: str | None = None  # For PII-redacted output

    @classmethod
    def allowed(
        cls,
        ctx: GuardContext | None = None,
        latency_ms: float = 0.0,
        rules_version: str = "",
    ) -> GuardResult:
        """Factory for a passing result."""
        return cls(
            blocked=False,
            action="allow",
            ctx=ctx,
            latency_ms=latency_ms,
            rules_version=rules_version,
        )

    @classmethod
    def blocked_result(
        cls,
        reason_code: str,
        layer: str,
        severity: Literal["low", "medium", "high", "critical"],
        scores: dict[str, float] | None = None,
        ctx: GuardContext | None = None,
        latency_ms: float = 0.0,
        rules_version: str = "",
    ) -> GuardResult:
        """Factory for a blocked result."""
        return cls(
            blocked=True,
            action="block",
            reason_code=reason_code,
            layer=layer,
            severity=severity,
            scores=scores or {},
            ctx=ctx,
            latency_ms=latency_ms,
            rules_version=rules_version,
        )
