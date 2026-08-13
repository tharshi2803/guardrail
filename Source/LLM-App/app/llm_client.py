"""LLM client — Anthropic Claude wrapper."""

from __future__ import annotations

import anthropic

from .config import settings


def get_client() -> anthropic.Anthropic:
    """Return a configured Anthropic client."""
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def ask_llm(
    system_prompt: str,
    user_message: str,
    model: str | None = None,
    client: anthropic.Anthropic | None = None,
) -> str:
    """Send a prompt to Claude and return the response text.

    Uses sync API — sufficient for a request-per-call pattern.
    """
    client = client or get_client()
    model = model or settings.LLM_MODEL

    try:
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text
    except anthropic.APIError as exc:
        return f"LLM error: {exc}"
