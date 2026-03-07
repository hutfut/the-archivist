from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from functools import reduce
from itertools import groupby
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.sql.elements import ColumnElement
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


_RRF_K = 60


def rrf_merge(
    ranked_lists: list[list[RetrievedChunk]],
    rrf_k: int = _RRF_K,
) -> list[RetrievedChunk]:
    """Merge multiple ranked result lists using Reciprocal Rank Fusion.

    Each chunk's RRF score is the sum of 1/(k + rank) across all lists it
    appears in, where rank is 1-indexed. Scores are normalized to [0, 1]
    by dividing by the theoretical maximum (all lists rank the chunk #1).
    Chunks are identified by (document_id, chunk_index) to deduplicate
    across lists.
    """
    n_lists = len(ranked_lists)
    if n_lists == 0:
        return []

    scores: dict[tuple[str, int], float] = {}
    chunk_map: dict[tuple[str, int], RetrievedChunk] = {}

    for ranked_list in ranked_lists:
        for rank, chunk in enumerate(ranked_list, start=1):
            key = (chunk.document_id, chunk.chunk_index)
            scores[key] = scores.get(key, 0.0) + 1.0 / (rrf_k + rank)
            if key not in chunk_map or chunk.similarity_score > chunk_map[key].similarity_score:
                chunk_map[key] = chunk

    max_rrf = n_lists / (rrf_k + 1)
    if max_rrf == 0:
        max_rrf = 1.0

    sorted_keys = sorted(scores.keys(), key=lambda k: scores[k], reverse=True)
    return [
        replace(chunk_map[key], similarity_score=scores[key] / max_rrf)
        for key in sorted_keys
    ]


class RetrievalService:
    """Retrieves relevant document chunks via hybrid search.

    Supports three retrieval modes:
    - "vector": pgvector cosine similarity only (original behavior)
    - "keyword": PostgreSQL full-text search only (BM25 via ts_rank)
    - "hybrid": both, merged with Reciprocal Rank Fusion (default)

    All modes apply post-retrieval deduplication to maximize context diversity.
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        retrieval_mode: str = "hybrid",
    ) -> None:
        self._embedding_service = embedding_service
        self._retrieval_mode = retrieval_mode

    async def _vector_search(
        self,
        query: str,
        session: AsyncSession,
        candidate_k: int,
    ) -> list[RetrievedChunk]:
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
        return [
            RetrievedChunk(
                document_id=row.document_id,
                filename=row.filename,
                chunk_content=row.content,
                chunk_index=row.chunk_index,
                similarity_score=float(row.similarity),
                section_heading=row.section_heading,
            )
            for row in result.all()
        ]

    @staticmethod
    def _build_or_tsquery(query: str) -> ColumnElement[bool]:
        """Build an OR-based tsquery with proper stemming.

        plainto_tsquery uses AND logic, which is too strict for natural
        language questions (no single chunk contains all query terms).
        Instead, we build individual plainto_tsquery per word and combine
        with || (OR) so partial matches contribute to ranking.
        """
        words = [w.strip() for w in query.split() if len(w.strip()) > 1]
        if not words:
            return func.plainto_tsquery("english", query)

        word_queries = [func.plainto_tsquery("english", w) for w in words]
        return reduce(lambda a, b: a.op("||")(b), word_queries)

    async def _keyword_search(
        self,
        query: str,
        session: AsyncSession,
        candidate_k: int,
    ) -> list[RetrievedChunk]:
        ts_query = self._build_or_tsquery(query)
        rank_expr = func.ts_rank(Chunk.search_vector, ts_query).label("rank")

        stmt = (
            select(
                Chunk.document_id,
                Document.filename,
                Chunk.content,
                Chunk.chunk_index,
                Chunk.section_heading,
                rank_expr,
            )
            .join(Document, Chunk.document_id == Document.id)
            .where(Chunk.search_vector.op("@@")(ts_query))
            .order_by(rank_expr.desc())
            .limit(candidate_k)
        )

        result = await session.execute(stmt)
        return [
            RetrievedChunk(
                document_id=row.document_id,
                filename=row.filename,
                chunk_content=row.content,
                chunk_index=row.chunk_index,
                similarity_score=float(row.rank),
                section_heading=row.section_heading,
            )
            for row in result.all()
        ]

    async def search(
        self,
        query: str,
        session: AsyncSession,
        top_k: int = 5,
        candidate_k: int = 20,
    ) -> list[RetrievedChunk]:
        """Find the top-k most relevant chunks using the configured retrieval mode.

        Over-fetches candidate_k results per source, then deduplicates down
        to top_k. In hybrid mode, vector and keyword results are merged via
        Reciprocal Rank Fusion before deduplication.
        """
        mode = self._retrieval_mode

        if mode == "vector":
            candidates = await self._vector_search(query, session, candidate_k)
        elif mode == "keyword":
            candidates = await self._keyword_search(query, session, candidate_k)
        elif mode == "hybrid":
            vector_results = await self._vector_search(query, session, candidate_k)
            keyword_results = await self._keyword_search(query, session, candidate_k)
            candidates = rrf_merge([vector_results, keyword_results])
            logger.info(
                "Hybrid search: %d vector + %d keyword -> %d merged for query: %.80s",
                len(vector_results),
                len(keyword_results),
                len(candidates),
                query,
            )
        else:
            raise ValueError(f"Unknown retrieval_mode: {mode!r}")

        deduped = deduplicate_chunks(candidates, final_k=top_k)
        logger.info(
            "Retrieved %d candidates, deduped to %d for query: %.80s",
            len(candidates),
            len(deduped),
            query,
        )
        return deduped
