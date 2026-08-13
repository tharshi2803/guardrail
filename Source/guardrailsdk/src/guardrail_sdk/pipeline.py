"""GuardrailPipeline — orchestrates L1-L6 layers."""

from __future__ import annotations

import time

import anthropic

from .config import GuardrailConfig, get_rules_version
from .layers.l1_normaliser import L1Normaliser
from .layers.l2_classifier import L2Classifier
from .layers.l3_prompt_guard import L3PromptGuard
from .layers.l4_rag_sanitiser import L4RAGSanitiser
from .layers.l5_output_scanner import L5OutputScanner
from .layers.l6_session_tracker import L6SessionTracker
from .models import GuardContext, GuardResult


class GuardrailPipeline:
    """Six-layer security pipeline wrapping LLM API calls.

    Usage::

        config = GuardrailConfig.from_yaml('guardrails.yaml')
        pipeline = GuardrailPipeline(config, anthropic_api_key='sk-...')

        ctx = pipeline.init_session('user-123')
        result = await pipeline.check_input(user_message, session_id='user-123')
        if result.blocked:
            raise HTTPException(400, result.reason_code)

        chunks = pipeline.sanitize_chunks(retrieved_chunks)
        # ... call LLM ...
        out = await pipeline.check_output(llm_response, ctx=ctx)
    """

    def __init__(
        self,
        config: GuardrailConfig,
        anthropic_api_key: str | None = None,
        rules_file: str | None = None,
    ) -> None:
        self._config = config
        self._rules_file = rules_file
        gc = config.guardrails

        # Anthropic client (optional — tests can pass None)
        self._anthropic = (
            anthropic.Anthropic(api_key=anthropic_api_key)
            if anthropic_api_key
            else None
        )

        # Initialise layers
        self._l1 = L1Normaliser(gc.input.normaliser)
        self._l2 = L2Classifier(gc.input.classifier, self._anthropic)
        self._l3 = L3PromptGuard(gc.input)
        self._l4 = L4RAGSanitiser(gc.input.rag_sanitiser)
        self._l5 = L5OutputScanner(gc.output, self._anthropic)
        self._l6 = L6SessionTracker(gc.session)

        # Track contexts per session
        self._contexts: dict[str, GuardContext] = {}

    @property
    def rules_version(self) -> str:
        if self._rules_file:
            return get_rules_version(self._rules_file)
        return "unknown"

    def update_config(self, config: GuardrailConfig) -> None:
        """Hot-swap the config (called by rules watcher)."""
        self._config = config
        gc = config.guardrails
        self._l1 = L1Normaliser(gc.input.normaliser)
        self._l2 = L2Classifier(gc.input.classifier, self._anthropic)
        self._l3 = L3PromptGuard(gc.input)
        self._l4 = L4RAGSanitiser(gc.input.rag_sanitiser)
        self._l5 = L5OutputScanner(gc.output, self._anthropic)
        self._l6 = L6SessionTracker(gc.session)

    def init_session(self, session_id: str = "default") -> GuardContext:
        """Run L3 to harden the system prompt for a session."""
        ctx = self._l3.harden(session_id)
        self._contexts[session_id] = ctx
        return ctx

    def _get_context(self, session_id: str) -> GuardContext:
        """Get or create context for a session."""
        if session_id not in self._contexts:
            self._contexts[session_id] = self.init_session(session_id)
        return self._contexts[session_id]

    async def check_input(
        self, message: str, session_id: str = "default"
    ) -> GuardResult:
        """Pre-inference check: L6 rate limit → L1 normalise → L2 classify."""
        start = time.perf_counter()
        ctx = self._get_context(session_id)
        rv = self.rules_version

        # L6 — rate limit
        rate_result = self._l6.check_rate_limit(session_id)
        if rate_result:
            rate_result.rules_version = rv
            rate_result.ctx = ctx
            return rate_result

        # L1 — normalise
        normalised, l1_result = self._l1.normalise(message)
        if l1_result:
            l1_result.rules_version = rv
            l1_result.ctx = ctx
            return l1_result

        # L2 — classify
        l2_result = await self._l2.classify(normalised, ctx)
        l2_result.rules_version = rv
        if normalised != message:
            l2_result.sanitised_text = normalised

        # Update suspicion on block
        if l2_result.blocked:
            max_score = max(l2_result.scores.values()) if l2_result.scores else 0.5
            self._l6.update_suspicion(session_id, max_score)

        l2_result.latency_ms = (time.perf_counter() - start) * 1000
        return l2_result

    def sanitize_chunks(self, chunks: list[dict]) -> list[dict]:
        """L4 — sanitise retrieved chunks."""
        return self._l4.sanitise_chunks(chunks)

    async def check_output(
        self, response: str, ctx: GuardContext
    ) -> GuardResult:
        """Post-inference check: L5 output scan."""
        result = await self._l5.scan(response, ctx)
        result.rules_version = self.rules_version

        # Update L6 suspicion if something flagged
        if result.blocked:
            self._l6.update_suspicion(ctx.session_id, 0.8)

        return result
