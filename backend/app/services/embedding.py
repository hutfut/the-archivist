from __future__ import annotations

import hashlib
import logging
import struct
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)

EMBEDDING_DIMENSION = 384


@runtime_checkable
class EmbeddingService(Protocol):
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts."""
        ...

    def embed_query(self, query: str) -> list[float]:
        """Generate an embedding for a single query string."""
        ...


class HuggingFaceEmbeddingService:
    """Production embedding service using sentence-transformers all-MiniLM-L6-v2."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        from langchain_huggingface import HuggingFaceEmbeddings

        self._model = HuggingFaceEmbeddings(model_name=model_name)
        logger.info("Loaded embedding model: %s", model_name)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return self._model.embed_documents(texts)

    def embed_query(self, query: str) -> list[float]:
        return self._model.embed_query(query)


class MockEmbeddingService:
    """Deterministic mock embedding service for tests.

    Produces consistent vectors based on text content hash so that
    identical inputs always yield identical embeddings. The vectors
    are not semantically meaningful but satisfy dimensional constraints.
    """

    def __init__(self, dimension: int = EMBEDDING_DIMENSION) -> None:
        self._dimension = dimension

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._hash_to_vector(t) for t in texts]

    def embed_query(self, query: str) -> list[float]:
        return self._hash_to_vector(query)

    def _hash_to_vector(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode()).digest()
        # Extend hash bytes to fill the required dimension
        repeated = digest * (self._dimension * 4 // len(digest) + 1)
        floats = struct.unpack(f"<{self._dimension}f", repeated[: self._dimension * 4])
        # Normalize to unit length for cosine similarity compatibility
        magnitude = sum(f * f for f in floats) ** 0.5
        if magnitude == 0:
            return [0.0] * self._dimension
        return [f / magnitude for f in floats]
