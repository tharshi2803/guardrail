"""Context assembly — XML-isolated prompt builder."""

from __future__ import annotations

_DEFAULT_SYSTEM = (
    "You are a helpful healthcare Q&A assistant. "
    "Answer only from the retrieved_context provided below. "
    "If the context does not contain the answer, say so."
)


def build_context(chunks: list[dict]) -> str:
    """Wrap each chunk in <doc> XML tags inside <retrieved_context>."""
    parts: list[str] = []
    for i, chunk in enumerate(chunks, start=1):
        source = chunk.get("metadata", {}).get("source", "unknown")
        row_idx = chunk.get("metadata", {}).get("row_index", "")
        parts.append(
            f'  <doc id="{i}" source="{source}" row="{row_idx}">'
            f'{chunk["content"]}'
            f"</doc>"
        )
    return "<retrieved_context>\n" + "\n".join(parts) + "\n</retrieved_context>"


def build_prompt(
    question: str,
    chunks: list[dict],
    system_prompt: str | None = None,
) -> tuple[str, str]:
    """Return (system_message, user_message) for the LLM call.

    The user_message contains the XML-isolated context plus the question.
    """
    system_msg = system_prompt or _DEFAULT_SYSTEM
    context_xml = build_context(chunks)
    user_msg = f"{context_xml}\n<user_question>{question}</user_question>"
    return system_msg, user_msg
