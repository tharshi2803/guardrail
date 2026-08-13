"""Retriever — query ChromaDB for relevant documents."""

from __future__ import annotations

import chromadb


def retrieve(
    query: str,
    collection: chromadb.Collection,
    top_k: int = 10,
    filters: dict[str, str] | None = None,
) -> list[dict]:
    """Embed *query* and return the top-k most similar chunks.

    Each result dict has keys: id, content, metadata, distance.

    Args:
        filters: Optional ChromaDB ``where`` filter dict.  Supports
            keys like ``doctor``, ``condition``, ``medication``,
            ``hospital``, ``admission_type``, ``test_results``,
            ``blood_type``, ``age_group``.
    """
    query_kwargs: dict = {"query_texts": [query], "n_results": top_k}
    if filters:
        query_kwargs["where"] = filters

    results = collection.query(**query_kwargs)

    chunks: list[dict] = []
    for i in range(len(results["ids"][0])):
        chunks.append(
            {
                "id": results["ids"][0][i],
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i] if results.get("distances") else None,
            }
        )
    return chunks
