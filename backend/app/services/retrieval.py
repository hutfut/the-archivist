from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.sql.expression import literal_column

from app.db.models import Chunk, Document

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.services.embedding import EmbeddingService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetrievedChunk:
    document_id: str
    filename: str
    chunk_content: str
    chunk_index: int
    similarity_score: float


class RetrievalService:
    """Retrieves relevant document chunks via pgvector cosine similarity.

    Uses direct SQLAlchemy queries against the existing chunks table
    with pgvector's <=> cosine distance operator, joined to the documents
    table for filename attribution.
    """

    def __init__(self, embedding_service: EmbeddingService) -> None:
        self._embedding_service = embedding_service

    async def search(
        self,
        query: str,
        session: AsyncSession,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        """Find the top-k most similar chunks to the query.

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
                similarity_expr,
            )
            .join(Document, Chunk.document_id == Document.id)
            .order_by(literal_column(distance_expr))
            .limit(top_k)
        )

        result = await session.execute(stmt)
        rows = result.all()

        return [
            RetrievedChunk(
                document_id=row.document_id,
                filename=row.filename,
                chunk_content=row.content,
                chunk_index=row.chunk_index,
                similarity_score=float(row.similarity),
            )
            for row in rows
        ]
