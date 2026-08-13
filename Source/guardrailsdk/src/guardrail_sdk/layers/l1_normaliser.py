"""L1 — Input normalisation layer.

Synchronous, deterministic. Strips encoding obfuscation before any
classifier sees the input.
"""

from __future__ import annotations

import base64
import re
import unicodedata

from ..config import NormaliserConfig
from ..models import GuardResult

_BASE64_RE = re.compile(r"(?<!\S)[A-Za-z0-9+/]{4,}={0,2}(?!\S)")
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"\+?\d[\d\s\-]{7,}\d")
_SSN_RE = re.compile(r"\d{3}-\d{2}-\d{4}")
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_PATIENT_ID_RE = re.compile(
    r"\b((?:patient\s*(?:id|#)|medical\s+record\s*(?:number|#)?|"
    r"record\s*(?:id|number|#)|mrn)\s*(?:is|=|:|#)?\s*)"
    r"([A-Za-z0-9][A-Za-z0-9-]{3,})",
    re.IGNORECASE,
)
_MOJIBAKE_FRAGMENT_RE = re.compile(r"(?:Ã|Â|â|ð|Ÿ|’|�|¦|¯|̄|¢|°)+")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
_WHITESPACE_RE = re.compile(r"\s+")


class L1Normaliser:
    """Normalise input text: Unicode NFKC, Base64 decode, token limit."""

    def __init__(self, config: NormaliserConfig) -> None:
        self._config = config

    def normalise(
        self, text: str, redact: bool = True
    ) -> tuple[str, GuardResult | None]:
        """Return (normalised_text, None) or (text, blocked_result).

        When ``redact`` is False, input PII redaction is skipped — used for the
        text handed to the LLM so that PII in the response is caught by the L5
        output scanner instead of being stripped before the model sees it.
        """
        result = text

        # 1. Unicode NFKC
        if self._config.unicode_nfkc:
            result = unicodedata.normalize("NFKC", result)

        # 2. Base64 decode
        if self._config.decode_base64:
            result = self._decode_base64(result)

        # 3. Remove common mojibake/control noise that NFKC cannot fix.
        result = self.clean_encoding_noise(result)

        # 4. Deterministic input PII redaction (skipped when redact=False).
        if redact:
            result = self.redact_pii(result)

        # 5. Token limit (rough: words / 0.75)
        approx_tokens = int(len(result.split()) / 0.75)
        if approx_tokens > self._config.max_tokens:
            return text, GuardResult.blocked_result(
                reason_code="token_limit_exceeded",
                layer="L1_normaliser",
                severity="medium",
                scores={"approx_tokens": float(approx_tokens)},
            )

        return result, None

    @staticmethod
    def redact_pii(text: str) -> str:
        """Redact direct identifiers in user input before retrieval or prompting."""
        text = _EMAIL_RE.sub("[EMAIL REDACTED]", text)
        text = _SSN_RE.sub("[SSN REDACTED]", text)
        text = _PHONE_RE.sub(_redact_phone_candidate, text)
        return _PATIENT_ID_RE.sub(r"\1[PATIENT ID REDACTED]", text)

    @staticmethod
    def clean_encoding_noise(text: str) -> str:
        """Remove common mojibake fragments and invisible control characters."""
        text = _CONTROL_RE.sub("", text)
        text = _MOJIBAKE_FRAGMENT_RE.sub("", text)
        return _WHITESPACE_RE.sub(" ", text).strip()

    @staticmethod
    def _decode_base64(text: str) -> str:
        """Find and decode Base64-encoded segments in text."""

        def _try_decode(match: re.Match) -> str:
            candidate = match.group(0)
            if not _looks_like_base64_payload(candidate):
                return candidate
            try:
                decoded = base64.b64decode(candidate, validate=True).decode(
                    "utf-8",
                    errors="replace",
                )
                # Only replace if decoded text looks like actual text
                if _looks_like_decoded_text(decoded):
                    return decoded
            except Exception:
                pass
            return candidate

        return _BASE64_RE.sub(_try_decode, text)


def _looks_like_base64_payload(candidate: str) -> bool:
    """Avoid decoding ordinary words that happen to use Base64 characters."""
    if len(candidate) >= 20:
        return True
    if candidate.endswith("="):
        return True
    return "+" in candidate or "/" in candidate


def _looks_like_decoded_text(decoded: str) -> bool:
    stripped = decoded.strip()
    if len(stripped) < 3:
        return False
    return all(char.isprintable() or char in "\r\n\t" for char in decoded)


def _redact_phone_candidate(match: re.Match[str]) -> str:
    candidate = match.group(0)
    if not _is_phone_candidate(candidate):
        return candidate
    return "[PHONE REDACTED]"


def _is_phone_candidate(candidate: str) -> bool:
    if _ISO_DATE_RE.fullmatch(candidate):
        return False

    digits = re.sub(r"\D", "", candidate)
    if candidate.strip().startswith("+"):
        return len(digits) >= 8

    if re.search(r"[\s\-]", candidate.strip()):
        return len(digits) >= 8

    return len(digits) >= 10
