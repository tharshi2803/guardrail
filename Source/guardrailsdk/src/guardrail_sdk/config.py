"""Pydantic configuration models matching guardrails.yaml schema."""

from __future__ import annotations

import hashlib
from pathlib import Path

import yaml
from pydantic import BaseModel


class NormaliserConfig(BaseModel):
    unicode_nfkc: bool = True
    decode_base64: bool = True
    max_tokens: int = 4096


class ClassifierThresholds(BaseModel):
    prompt_injection: float = 0.85
    jailbreak_roleplay: float = 0.80
    harmful_content: float = 0.75
    pii_exfil: float = 0.70
    dos: float = 0.65


class ClassifierConfig(BaseModel):
    backend: str = "claude-haiku"
    thresholds: ClassifierThresholds = ClassifierThresholds()


class RAGSanitiserConfig(BaseModel):
    enabled: bool = True
    injection_threshold: float = 0.70
    patterns: list[str] = []


class InputConfig(BaseModel):
    normaliser: NormaliserConfig = NormaliserConfig()
    classifier: ClassifierConfig = ClassifierConfig()
    rag_sanitiser: RAGSanitiserConfig = RAGSanitiserConfig()
    system_prompt_template: str = ""


class HarmfulContentConfig(BaseModel):
    enabled: bool = True
    categories: list[str] = []


class PIIScannerConfig(BaseModel):
    regex: bool = True
    ner: bool = False


class CanaryCheckConfig(BaseModel):
    enabled: bool = True


class OutputConfig(BaseModel):
    harmful_content: HarmfulContentConfig = HarmfulContentConfig()
    pii_scanner: PIIScannerConfig = PIIScannerConfig()
    canary_check: CanaryCheckConfig = CanaryCheckConfig()


class RateLimitConfig(BaseModel):
    rpm: int = 60
    tpm: int = 100000


class SessionConfig(BaseModel):
    rate_limit: RateLimitConfig = RateLimitConfig()
    suspicion_decay_seconds: int = 300


class GuardrailsConfig(BaseModel):
    input: InputConfig = InputConfig()
    output: OutputConfig = OutputConfig()
    session: SessionConfig = SessionConfig()


class GuardrailConfig(BaseModel):
    guardrails: GuardrailsConfig = GuardrailsConfig()

    @classmethod
    def from_yaml(cls, path: str | Path) -> GuardrailConfig:
        """Load and validate config from a YAML file."""
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return cls.model_validate(data)


def get_rules_version(path: str | Path) -> str:
    """Return the SHA-256 hash of a rules file."""
    content = Path(path).read_bytes()
    return f"sha256:{hashlib.sha256(content).hexdigest()[:12]}"
