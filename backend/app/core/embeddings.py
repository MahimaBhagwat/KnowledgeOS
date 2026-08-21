from __future__ import annotations

from typing import List

import litellm

from app.core.config import settings

_DEFAULT_EMBEDDING_MODEL = "gemini/text-embedding-004"


def _resolve_embedding_model() -> str:
    model_name = (settings.llm_embedding_model_name or "").strip()
    return model_name or _DEFAULT_EMBEDDING_MODEL


def _extract_embeddings(response: object, expected_count: int) -> List[List[float]]:
    data = getattr(response, "data", None)
    if data is None and isinstance(response, dict):
        data = response.get("data")
    if not data:
        raise RuntimeError("LiteLLM embedding response did not include embedding data.")

    vectors: List[List[float]] = []
    for item in data:
        vector = getattr(item, "embedding", None)
        if vector is None and isinstance(item, dict):
            vector = item.get("embedding")
        if vector is None:
            raise RuntimeError("LiteLLM embedding response item did not include an embedding vector.")
        vectors.append([float(value) for value in vector])

    if len(vectors) != expected_count:
        raise RuntimeError(f"LiteLLM returned {len(vectors)} embeddings for {expected_count} input texts.")
    return vectors


def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for a batch of texts using LiteLLM."""
    if not texts:
        return []

    response = litellm.embedding(
        model=_resolve_embedding_model(),
        input=texts,
        api_key=settings.llm_api_key.get_secret_value(),
    )
    return _extract_embeddings(response, len(texts))


def generate_query_embedding(query: str) -> List[float]:
    """Generate an embedding for a single search query using LiteLLM."""
    vectors = generate_embeddings([query])
    if not vectors:
        raise RuntimeError("LiteLLM returned no embedding for the query.")
    return vectors[0]
