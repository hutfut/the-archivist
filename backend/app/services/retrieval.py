from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from itertools import groupby
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.sql.expression import literal_column

from app.db.models import Chunk, Document

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.services.embedding import EmbeddingService

logger = logging.getLogger(__name__)

_OVERLAP_THRESHOLD = 0.60


@dataclass(frozen=True)
class RetrievedChunk:
    document_id: str
    filename: str
    chunk_content: str
    chunk_index: int
    similarity_score: float
    section_heading: str | None = None


def _token_set(text: str) -> set[str]:
    return set(text.lower().split())


def _jaccard_similarity(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def _merge_adjacent_chunks(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    """Merge chunks that are from the same document and have consecutive chunk_index values.

    Within each same-document group of consecutive chunks, merge content in
    chunk_index order, keep the highest similarity score, and use the lowest
    chunk_index as the representative index.
    """
    if len(chunks) <= 1:
        return list(chunks)

    doc_groups: dict[str, list[RetrievedChunk]] = {}
    for chunk in chunks:
        doc_groups.setdefault(chunk.document_id, []).append(chunk)

    merged: list[RetrievedChunk] = []
    for doc_id, doc_chunks in doc_groups.items():
        sorted_chunks = sorted(doc_chunks, key=lambda c: c.chunk_index)

        for _, run in groupby(
            enumerate(sorted_chunks),
            key=lambda pair: pair[1].chunk_index - pair[0],
        ):
            run_chunks = [c for _, c in run]
            if len(run_chunks) == 1:
                merged.append(run_chunks[0])
            else:
                combined_content = "\n\n".join(c.chunk_content for c in run_chunks)
                best_score = max(c.similarity_score for c in run_chunks)
                merged.append(replace(
                    run_chunks[0],
                    chunk_content=combined_content,
                    similarity_score=best_score,
                ))

    return merged


def _is_substring_of_existing(text: str, existing_texts: list[str]) -> bool:
    """Check if text is a substring of any existing text (or vice versa)."""
    normalized = text.strip().lower()
    for existing in existing_texts:
        existing_norm = existing.strip().lower()
        if normalized in existing_norm or existing_norm in normalized:
            return True
    return False


def _drop_overlapping(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    """Drop lower-scoring chunks that overlap with a higher-scoring chunk.

    Two-pass filtering:
    1. Substring containment -- if chunk A's content is contained within
       chunk B's (or vice versa), drop the lower-scored one.
    2. Jaccard token overlap -- drop chunks exceeding the overlap threshold.
    """
    scored = sorted(chunks, key=lambda c: c.similarity_score, reverse=True)
    kept: list[RetrievedChunk] = []
    kept_tokens: list[set[str]] = []
    kept_texts: list[str] = []

    for chunk in scored:
        if _is_substring_of_existing(chunk.chunk_content, kept_texts):
            continue

        tokens = _token_set(chunk.chunk_content)
        is_duplicate = any(
            _jaccard_similarity(tokens, existing) > _OVERLAP_THRESHOLD
            for existing in kept_tokens
        )
        if not is_duplicate:
            kept.append(chunk)
            kept_tokens.append(tokens)
            kept_texts.append(chunk.chunk_content)

    return kept


def deduplicate_chunks(
    chunks: list[RetrievedChunk],
    final_k: int = 5,
) -> list[RetrievedChunk]:
    """Remove near-duplicate chunks via adjacent merging and overlap filtering.

    1. Merge consecutive same-document chunks into single blocks.
    2. Drop chunks where one is a substring of another (keep higher-scored).
    3. Drop chunks with >60% Jaccard token overlap (keep higher-scored).
    4. Return top final_k by similarity score.
    """
    if len(chunks) <= 1:
        return list(chunks)

    merged = _merge_adjacent_chunks(chunks)
    unique = _drop_overlapping(merged)

    result = sorted(unique, key=lambda c: c.similarity_score, reverse=True)
    return result[:final_k]


class RetrievalService:
    """Retrieves relevant document chunks via pgvector cosine similarity.

    Uses direct SQLAlchemy queries against the existing chunks table
    with pgvector's <=> cosine distance operator, joined to the documents
    table for filename attribution. Applies post-retrieval deduplication
    to maximize context diversity.
    """

    def __init__(self, embedding_service: EmbeddingService) -> None:
        self._embedding_service = embedding_service

    async def search(
        self,
        query: str,
        session: AsyncSession,
        top_k: int = 5,
        candidate_k: int = 10,
    ) -> list[RetrievedChunk]:
        """Find the top-k most similar chunks to the query.

        Over-fetches candidate_k results, then deduplicates down to top_k.
        Returns chunks ordered by similarity (highest first). The similarity
        score is 1 - cosine_distance, so higher is better.
        """
        query_embedding = self._embedding_service.embed_query(query)
        embedding_literal = f"[{','.join(str(v) for v in query_embedding)}]"

        distance_expr = f"chunks.embedding <=> '{embedding_literal}'::vector"
        similarity_expr = literal_column(
            f"(1 - ({distance_expr}))"
        ).label("similarity")

        stmt = (
            select(
                Chunk.document_id,
                Document.filename,
                Chunk.content,
                Chunk.chunk_index,
                Chunk.section_heading,
                similarity_expr,
            )
            .join(Document, Chunk.document_id == Document.id)
            .order_by(literal_column(distance_expr))
            .limit(candidate_k)
        )

        result = await session.execute(stmt)
        rows = result.all()

        candidates = [
            RetrievedChunk(
                document_id=row.document_id,
                filename=row.filename,
                chunk_content=row.content,
                chunk_index=row.chunk_index,
                similarity_score=float(row.similarity),
                section_heading=row.section_heading,
            )
            for row in rows
        ]

        deduped = deduplicate_chunks(candidates, final_k=top_k)
        logger.info(
            "Retrieved %d candidates, deduped to %d for query: %.80s",
            len(candidates),
            len(deduped),
            query,
        )
        return deduped
