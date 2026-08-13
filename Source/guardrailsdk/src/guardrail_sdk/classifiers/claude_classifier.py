"""Claude classifier backend for L2 and L5."""

from __future__ import annotations

import json


async def classify_input(
    client, model: str, text: str
) -> dict[str, float]:
    """Send a classification prompt to Claude and return label scores."""
    prompt = (
        "Analyse the following text and return ONLY a JSON object with scores "
        "0.0-1.0 for: prompt_injection, jailbreak_roleplay, harmful_content, "
        f"pii_exfil, dos.\n\nText: {text[:2000]}"
    )
    try:
        response = client.messages.create(
            model=model,
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        return json.loads(response.content[0].text.strip())
    except (json.JSONDecodeError, Exception):
        return {
            "prompt_injection": 0.0,
            "jailbreak_roleplay": 0.0,
            "harmful_content": 0.0,
            "pii_exfil": 0.0,
            "dos": 0.0,
        }


async def classify_harmful(
    client, model: str, text: str, categories: list[str]
) -> dict[str, float]:
    """Send a harmful-content classification prompt to Claude."""
    cats = ", ".join(categories)
    prompt = (
        f"Analyse for harmful content in categories: {cats}. "
        f"Return ONLY JSON with a 0.0-1.0 score per category.\n\nText: {text[:500]}"
    )
    try:
        response = client.messages.create(
            model=model,
            max_tokens=128,
            messages=[{"role": "user", "content": prompt}],
        )
        return json.loads(response.content[0].text.strip())
    except (json.JSONDecodeError, Exception):
        return {c: 0.0 for c in categories}
