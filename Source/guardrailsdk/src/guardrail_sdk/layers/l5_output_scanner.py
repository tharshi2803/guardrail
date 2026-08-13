"""L5 — Output scanner layer.

Post-inference layer that scans the raw LLM response before it is
returned to the client. Runs harmful content, PII, and canary checks
in parallel.
"""

from __future__ import annotations

import asyncio
import re
import time

from ..config import OutputConfig
from ..models import GuardContext, GuardResult

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"\+?\d[\d\s\-]{7,}\d")
_SSN_RE = re.compile(r"\d{3}-\d{2}-\d{4}")
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_PERSON_CONTEXT_RE = re.compile(
    r"\b((?:patient|person|doctor|physician|clinician|named)\s+)"
    r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b"
)
_COUNTRIES = (
    "Afghanistan", "Albania", "Algeria", "Argentina", "Australia", "Austria",
    "Bangladesh", "Belgium", "Brazil", "Canada", "Chile", "China",
    "Colombia", "Denmark", "Egypt", "Finland", "France", "Germany",
    "Greece", "India", "Indonesia", "Iran", "Iraq", "Ireland", "Israel",
    "Italy", "Japan", "Malaysia", "Mexico", "Netherlands", "New Zealand",
    "Nigeria", "Norway", "Pakistan", "Philippines", "Poland", "Portugal",
    "Russia", "Saudi Arabia", "Singapore", "South Africa", "South Korea",
    "Spain", "Sri Lanka", "Sweden", "Switzerland", "Thailand", "Turkey",
    "Ukraine", "United Arab Emirates", "United Kingdom", "United States",
    "USA", "Vietnam",
)
_COUNTRY_RE = re.compile(
    r"\b(" + "|".join(re.escape(country) for country in _COUNTRIES) + r")\b",
    re.IGNORECASE,
)


class L5OutputScanner:
    """Scan LLM output for harmful content, PII leaks, and canary exposure."""

    def __init__(self, config: OutputConfig, anthropic_client=None) -> None:
        self._config = config
        self._client = anthropic_client

    async def scan(self, response: str, ctx: GuardContext) -> GuardResult:
        """Run all output checks in parallel. Return the worst result."""
        start = time.perf_counter()

        canary_task = asyncio.ensure_future(self._check_canary(response, ctx))
        pii_task = asyncio.ensure_future(self._scan_pii(response))
        harmful_task = asyncio.ensure_future(self._check_harmful(response))

        canary_result, pii_result, harmful_result = await asyncio.gather(
            canary_task, pii_task, harmful_task
        )

        latency = (time.perf_counter() - start) * 1000

        # Canary is highest priority
        if canary_result:
            canary_result.latency_ms = latency
            canary_result.ctx = ctx
            return canary_result

        # Harmful content
        if harmful_result:
            harmful_result.latency_ms = latency
            harmful_result.ctx = ctx
            return harmful_result

        # PII — sanitise rather than block
        if pii_result:
            pii_result.latency_ms = latency
            pii_result.ctx = ctx
            return pii_result

        return GuardResult.allowed(ctx=ctx, latency_ms=latency)

    async def _check_canary(
        self, response: str, ctx: GuardContext
    ) -> GuardResult | None:
        """Check if the canary token appears in the output."""
        if (
            self._config.canary_check.enabled
            and ctx.canary_token
            and ctx.canary_token in response
        ):
            return GuardResult.blocked_result(
                reason_code="canary_exposed",
                layer="L5_output_scanner",
                severity="critical",
            )
        return None

    async def _scan_pii(self, response: str) -> GuardResult | None:
        """Detect PII via configured scanners. Return a sanitise result if found."""
        if not self._config.pii_scanner.regex and not self._config.pii_scanner.ner:
            return None

        has_regex_pii = False
        if self._config.pii_scanner.regex:
            has_email = _EMAIL_RE.search(response)
            has_phone = any(_is_phone_candidate(m.group(0)) for m in _PHONE_RE.finditer(response))
            has_ssn = _SSN_RE.search(response)
            has_regex_pii = bool(has_email or has_phone or has_ssn)

        has_ner_pii = self._config.pii_scanner.ner and _has_ner_pii(response)

        if has_regex_pii or has_ner_pii:
            sanitised = self.sanitise_pii(
                response,
                use_regex=self._config.pii_scanner.regex,
                use_ner=self._config.pii_scanner.ner,
            )
            result = GuardResult(
                blocked=False,
                action="sanitise",
                reason_code="pii_detected",
                layer="L5_output_scanner",
                severity="medium",
                scores={},
                sanitised_text=sanitised,
            )
            return result
        return None

    async def _check_harmful(self, response: str) -> GuardResult | None:
        """Check for harmful content using LLM classifier (if available)."""
        if not self._config.harmful_content.enabled or not self._client:
            return None

        try:
            categories = ", ".join(self._config.harmful_content.categories)
            prompt = (
                f"Analyse this text for harmful content in categories: {categories}. "
                f"Return ONLY a JSON object with a score 0.0-1.0 for each category. "
                f"Text: {response[:500]}"
            )
            resp = self._client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=128,
                messages=[{"role": "user", "content": prompt}],
            )
            import json

            scores = json.loads(resp.content[0].text.strip())
            for cat, score in scores.items():
                if score >= 0.75:
                    return GuardResult.blocked_result(
                        reason_code="harmful_content",
                        layer="L5_output_scanner",
                        severity="critical",
                        scores=scores,
                    )
        except Exception:
            pass
        return None

    @staticmethod
    def sanitise_pii(
        text: str,
        use_regex: bool = True,
        use_ner: bool = False,
    ) -> str:
        """Replace detected PII with redaction placeholders."""
        if use_regex:
            text = _EMAIL_RE.sub("[EMAIL REDACTED]", text)
            text = _SSN_RE.sub("[SSN REDACTED]", text)
            text = _PHONE_RE.sub(_redact_phone_candidate, text)
        if use_ner:
            text = _PERSON_CONTEXT_RE.sub(r"\1[PERSON REDACTED]", text)
            text = _COUNTRY_RE.sub("[LOCATION REDACTED]", text)
        return text


def _redact_phone_candidate(match: re.Match[str]) -> str:
    """Redact phone-like values without masking ISO dates."""
    candidate = match.group(0)
    if not _is_phone_candidate(candidate):
        return candidate
    return "[PHONE REDACTED]"


def _is_phone_candidate(candidate: str) -> bool:
    """Return True for phone-like values, but not dates or clinical codes."""
    if _ISO_DATE_RE.fullmatch(candidate):
        return False

    digits = re.sub(r"\D", "", candidate)
    if candidate.strip().startswith("+"):
        return len(digits) >= 8

    has_phone_separator = bool(re.search(r"[\s\-]", candidate.strip()))
    if has_phone_separator:
        return len(digits) >= 8

    # Avoid redacting compact clinical vocab/code values such as SNOMED
    # 735029006. Plain digit-only phone numbers are usually at least 10 digits.
    return len(digits) >= 10


def _has_ner_pii(text: str) -> bool:
    """Return True for lightweight NER-style entities configured as PII."""
    return _PERSON_CONTEXT_RE.search(text) is not None or _COUNTRY_RE.search(text) is not None
