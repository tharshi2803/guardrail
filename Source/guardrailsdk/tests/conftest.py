"""Shared test fixtures for the Guardrail SDK."""

from __future__ import annotations

import textwrap
from unittest.mock import MagicMock

import pytest

from guardrail_sdk.config import GuardrailConfig
from guardrail_sdk.models import GuardContext


@pytest.fixture()
def sample_config(tmp_path) -> GuardrailConfig:
    """Return a GuardrailConfig loaded from a test YAML."""
    yaml_content = textwrap.dedent("""\
        guardrails:
          input:
            normaliser:
              unicode_nfkc: true
              decode_base64: true
              max_tokens: 100
            classifier:
              backend: claude-haiku
              thresholds:
                prompt_injection: 0.85
                jailbreak_roleplay: 0.80
                harmful_content: 0.75
                pii_exfil: 0.70
                dos: 0.65
            rag_sanitiser:
              enabled: true
              injection_threshold: 0.70
              patterns:
                - "ignore previous instructions"
                - "developer mode"
                - "pretend you are"
            system_prompt_template: |
              You are a helpful assistant. Answer only from retrieved_context.
          output:
            harmful_content:
              enabled: true
              categories:
                - cbrn
                - self_harm
            pii_scanner:
              regex: true
              ner: false
            canary_check:
              enabled: true
          session:
            rate_limit:
              rpm: 5
              tpm: 10000
            suspicion_decay_seconds: 300
    """)
    yaml_file = tmp_path / "guardrails.yaml"
    yaml_file.write_text(yaml_content)
    return GuardrailConfig.from_yaml(yaml_file)


@pytest.fixture()
def guard_context() -> GuardContext:
    """Return a GuardContext with a known canary token."""
    return GuardContext(
        canary_token="test-canary-12345",
        session_id="test-session",
        system_prompt="Test system prompt [CANARY:test-canary-12345]",
    )


@pytest.fixture()
def mock_anthropic():
    """Mock Anthropic client factory."""

    def _make(response_text: str):
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text=response_text)]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_msg
        return mock_client

    return _make
