from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.services.text_extraction import extract_text

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.services.embedding import EmbeddingService

logger = logging.getLogger(__name__)

DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 100


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[str]:
    """Split text into overlapping chunks using recursive character splitting.

    Args:
        text: The text to split.
        chunk_size: Maximum characters per chunk.
        chunk_overlap: Number of overlapping characters between adjacent chunks.

    Returns:
        List of text chunks, or empty list if text is empty.
    """
    if not text.strip():
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        strip_whitespace=True,
    )
    return splitter.split_text(text)


@runtime_checkable
class DocumentProcessor(Protocol):
    async def process(
        self,
        doc_id: str,
        file_path: Path,
        content_type: str,
        session: AsyncSession,
    ) -> int:
        """Process a document: extract text, chunk, embed, store.

        Returns the number of chunks created.
        """
        ...


class PipelineProcessor:
    """Production document processor: extract -> chunk -> embed -> store."""

    def __init__(self, embedding_service: EmbeddingService) -> None:
        self._embedding_service = embedding_service

    async def process(
        self,
        doc_id: str,
        file_path: Path,
        content_type: str,
        session: AsyncSession,
    ) -> int:
        from app.db.models import Chunk

        text = extract_text(file_path, content_type)
        if not text:
            logger.info("Document %s produced no text; skipping embedding", doc_id)
            return 0

        chunks = chunk_text(text)
        if not chunks:
            return 0

        embeddings = self._embedding_service.embed_texts(chunks)

        now = datetime.now(timezone.utc)
        for i, (chunk_text_content, embedding) in enumerate(zip(chunks, embeddings)):
            chunk = Chunk(
                id=str(uuid.uuid4()),
                document_id=doc_id,
                chunk_index=i,
                content=chunk_text_content,
                embedding=embedding,
                created_at=now,
            )
            session.add(chunk)

        await session.flush()
        logger.info("Processed document %s: %d chunks created", doc_id, len(chunks))
        return len(chunks)
