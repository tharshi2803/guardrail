"""Tests for L3 — System prompt hardening."""

from guardrail_sdk.config import InputConfig
from guardrail_sdk.layers.l3_prompt_guard import L3PromptGuard


def test_canary_injected():
    """System prompt should contain a CANARY token."""
    config = InputConfig(system_prompt_template="You are a helpful assistant.")
    l3 = L3PromptGuard(config)
    ctx = l3.harden("session-1")
    assert "[CANARY:" in ctx.system_prompt
    assert ctx.canary_token in ctx.system_prompt


def test_guard_context_contains_canary():
    """GuardContext should have the canary token set."""
    config = InputConfig(system_prompt_template="Test template.")
    l3 = L3PromptGuard(config)
    ctx = l3.harden("session-2")
    assert len(ctx.canary_token) > 0
    assert ctx.session_id == "session-2"


def test_override_resistance_appended():
    """Hardened prompt should include override-resistance instructions."""
    config = InputConfig(system_prompt_template="Base prompt.")
    l3 = L3PromptGuard(config)
    ctx = l3.harden("session-3")
    assert "prompt injection attempt" in ctx.system_prompt.lower()
    assert "refuse" in ctx.system_prompt.lower()
