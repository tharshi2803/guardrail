"""L4 — RAG / context sanitiser layer.

Scans each retrieved document chunk for indirect prompt injection
before context assembly. Catches malicious instructions embedded
inside documents.
"""

from __future__ import annotations

import re

from ..config import RAGSanitiserConfig


class L4RAGSanitiser:
    """Per-chunk injection scanner using regex patterns."""

    def __init__(self, config: RAGSanitiserConfig) -> None:
        self._config = config
        self._patterns = [
            re.compile(re.escape(p), re.IGNORECASE)
            for p in config.patterns
        ]

    def sanitise_chunks(self, chunks: list[dict]) -> list[dict]:
        """Scan chunks and quarantine any containing injection patterns.

        Returns a new list — quarantined chunks have their content replaced.
        """
        if not self._config.enabled:
            return chunks

        cleaned: list[dict] = []
        for chunk in chunks:
            content = chunk.get("content", "")
            source = chunk.get("metadata", {}).get("source", "unknown")

            is_injected = any(p.search(content) for p in self._patterns)

            if is_injected:
                cleaned.append(
                    {
                        **chunk,
                        "content": f"[CONTENT REMOVED: injection detected, source: {source}]",
                        "metadata": {**chunk.get("metadata", {}), "quarantined": True},
                    }
                )
            else:
                cleaned.append(chunk)

        return cleaned
