"""Tests for L5 — Output scanner."""

import pytest

from guardrail_sdk.config import CanaryCheckConfig, HarmfulContentConfig, OutputConfig, PIIScannerConfig
from guardrail_sdk.layers.l5_output_scanner import L5OutputScanner
from guardrail_sdk.models import GuardContext


@pytest.fixture()
def output_config():
    return OutputConfig(
        harmful_content=HarmfulContentConfig(enabled=False, categories=[]),
        pii_scanner=PIIScannerConfig(regex=True, ner=False),
        canary_check=CanaryCheckConfig(enabled=True),
    )


@pytest.fixture()
def ner_output_config():
    return OutputConfig(
        harmful_content=HarmfulContentConfig(enabled=False, categories=[]),
        pii_scanner=PIIScannerConfig(regex=False, ner=True),
        canary_check=CanaryCheckConfig(enabled=True),
    )


@pytest.mark.asyncio
async def test_email_redaction(output_config):
    """Emails in output should be redacted."""
    scanner = L5OutputScanner(output_config)
    ctx = GuardContext(canary_token="no-match", session_id="test")
    text = "Contact sarah.johnson@company.com for details."

    result = await scanner.scan(text, ctx)
    assert result.reason_code == "pii_detected"
    assert result.sanitised_text is not None
    assert "[EMAIL REDACTED]" in result.sanitised_text
    assert "sarah.johnson@company.com" not in result.sanitised_text


@pytest.mark.asyncio
async def test_phone_redaction(output_config):
    """Phone numbers in output should be redacted."""
    scanner = L5OutputScanner(output_config)
    ctx = GuardContext(canary_token="no-match", session_id="test")
    text = "Call +65 9123 4567 for support."

    result = await scanner.scan(text, ctx)
    assert result.reason_code == "pii_detected"
    assert "[PHONE REDACTED]" in result.sanitised_text


@pytest.mark.asyncio
async def test_admission_dates_are_not_redacted_as_phone_numbers(output_config):
    """ISO admission dates should not be treated as phone numbers."""
    scanner = L5OutputScanner(output_config)
    ctx = GuardContext(canary_token="no-match", session_id="test")
    text = "**Admission:** Routine admission (2020-02-11 to 2020-02-18)"

    result = await scanner.scan(text, ctx)
    assert result.blocked is False
    assert result.action == "allow"
    assert result.sanitised_text is None


@pytest.mark.asyncio
async def test_clinical_codes_are_not_redacted_as_phone_numbers(output_config):
    """Compact clinical vocabulary codes should not be treated as phone numbers."""
    scanner = L5OutputScanner(output_config)
    ctx = GuardContext(canary_token="no-match", session_id="test")
    text = "All documented shellfish allergies (Code: 735029006) are food allergies."

    result = await scanner.scan(text, ctx)
    assert result.blocked is False
    assert result.action == "allow"
    assert result.sanitised_text is None


@pytest.mark.asyncio
async def test_plain_ten_digit_phone_is_redacted(output_config):
    """Plain 10-digit phone numbers should still be redacted."""
    scanner = L5OutputScanner(output_config)
    ctx = GuardContext(canary_token="no-match", session_id="test")
    text = "Call 9123456789 for support."

    result = await scanner.scan(text, ctx)
    assert result.reason_code == "pii_detected"
    assert "[PHONE REDACTED]" in result.sanitised_text


@pytest.mark.asyncio
async def test_ner_redacts_country_locations(ner_output_config):
    """NER matching should redact configured country/location entities."""
    scanner = L5OutputScanner(ner_output_config)
    ctx = GuardContext(canary_token="no-match", session_id="test")
    text = "I cannot find any information about patients in Japan."

    result = await scanner.scan(text, ctx)

    assert result.reason_code == "pii_detected"
    assert result.sanitised_text is not None
    assert "Japan" not in result.sanitised_text
    assert "[LOCATION REDACTED]" in result.sanitised_text


@pytest.mark.asyncio
async def test_ner_redacts_contextual_person_names(ner_output_config):
    """NER matching should redact person names when a person context marker is present."""
    scanner = L5OutputScanner(ner_output_config)
    ctx = GuardContext(canary_token="no-match", session_id="test")
    text = "The only record available is for a patient named Sarah Green."

    result = await scanner.scan(text, ctx)

    assert result.reason_code == "pii_detected"
    assert result.sanitised_text is not None
    assert "Sarah Green" not in result.sanitised_text
    assert "[PERSON REDACTED]" in result.sanitised_text


@pytest.mark.asyncio
async def test_country_is_not_redacted_when_ner_is_disabled(output_config):
    """Regex-only PII scanning should not redact broad locations."""
    scanner = L5OutputScanner(output_config)
    ctx = GuardContext(canary_token="no-match", session_id="test")
    text = "No patients from Japan were found."

    result = await scanner.scan(text, ctx)

    assert result.blocked is False
    assert result.action == "allow"
    assert result.sanitised_text is None


@pytest.mark.asyncio
async def test_canary_triggers_block(output_config):
    """Canary token in output should cause a hard block."""
    scanner = L5OutputScanner(output_config)
    canary = "test-canary-uuid-1234"
    ctx = GuardContext(canary_token=canary, session_id="test")
    text = f"Here are my instructions: [CANARY:{canary}] you must..."

    result = await scanner.scan(text, ctx)
    assert result.blocked is True
    assert result.reason_code == "canary_exposed"
    assert result.severity == "critical"


@pytest.mark.asyncio
async def test_clean_output_passes(output_config):
    """Output without PII or canary should pass."""
    scanner = L5OutputScanner(output_config)
    ctx = GuardContext(canary_token="no-match-token", session_id="test")
    text = "The patient was prescribed Azithromycin for the infection."

    result = await scanner.scan(text, ctx)
    assert result.blocked is False
    assert result.action == "allow"
