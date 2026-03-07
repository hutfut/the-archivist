from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from app.services.text_extraction import extract_text

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.services.embedding import EmbeddingService

logger = logging.getLogger(__name__)

_processor: PipelineProcessor | None = None

DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200

_MARKDOWN_HEADERS = [
    ("#", "h1"),
    ("##", "h2"),
    ("###", "h3"),
]


@dataclass(frozen=True)
class ChunkWithHeading:
    """A text chunk with an optional section heading path."""

    content: str
    section_heading: str | None = None


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


def _build_heading_path(metadata: dict[str, str]) -> str | None:
    """Build a ' > '-separated heading path from MarkdownHeaderTextSplitter metadata."""
    parts = [metadata[key] for key in ("h1", "h2", "h3") if key in metadata]
    return " > ".join(parts) if parts else None


def chunk_markdown(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[ChunkWithHeading]:
    """Split markdown text by section headers, sub-splitting oversized sections.

    First pass: split on #, ##, ### headers (keeping each section coherent).
    Second pass: any section exceeding chunk_size is further split using
    RecursiveCharacterTextSplitter; sub-chunks inherit the parent heading.

    Args:
        text: Markdown text to split.
        chunk_size: Maximum characters per chunk (for sub-splitting).
        chunk_overlap: Overlap characters for sub-splits.

    Returns:
        List of ChunkWithHeading, or empty list if text is empty.
    """
    if not text.strip():
        return []

    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=_MARKDOWN_HEADERS,
        strip_headers=True,
    )
    sections = header_splitter.split_text(text)

    if not sections:
        plain_chunks = chunk_text(text, chunk_size, chunk_overlap)
        return [ChunkWithHeading(content=c) for c in plain_chunks]

    size_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        strip_whitespace=True,
    )

    result: list[ChunkWithHeading] = []
    for section in sections:
        heading = _build_heading_path(section.metadata)
        content = section.page_content.strip()
        if not content:
            continue

        if len(content) <= chunk_size:
            result.append(ChunkWithHeading(content=content, section_heading=heading))
        else:
            sub_chunks = size_splitter.split_text(content)
            for sub in sub_chunks:
                result.append(ChunkWithHeading(content=sub, section_heading=heading))

    return result


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


def _is_markdown(content_type: str) -> bool:
    return content_type == "text/markdown"


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

        try:
            text = extract_text(file_path, content_type)
        except (ValueError, OSError) as exc:
            logger.warning("Failed to extract text from document %s: %s", doc_id, exc)
            return 0
        except Exception:
            logger.exception("Unexpected error extracting text from document %s", doc_id)
            return 0

        if not text:
            logger.info("Document %s produced no text; skipping embedding", doc_id)
            return 0

        if _is_markdown(content_type):
            chunks_with_headings = chunk_markdown(text)
        else:
            plain_chunks = chunk_text(text)
            chunks_with_headings = [ChunkWithHeading(content=c) for c in plain_chunks]

        if not chunks_with_headings:
            return 0

        texts = [c.content for c in chunks_with_headings]
        embeddings = self._embedding_service.embed_texts(texts)

        now = datetime.now(timezone.utc)
        for i, (cwh, embedding) in enumerate(zip(chunks_with_headings, embeddings)):
            chunk = Chunk(
                id=str(uuid.uuid4()),
                document_id=doc_id,
                chunk_index=i,
                content=cwh.content,
                section_heading=cwh.section_heading,
                embedding=embedding,
                created_at=now,
            )
            session.add(chunk)

        await session.flush()
        logger.info("Processed document %s: %d chunks created", doc_id, len(chunks_with_headings))
        return len(chunks_with_headings)


def init_processor(embedding_service: EmbeddingService) -> None:
    """Initialize the global document processor with the given embedding service."""
    global _processor
    _processor = PipelineProcessor(embedding_service)


def get_processor() -> PipelineProcessor:
    """FastAPI dependency that returns the document processor."""
    if _processor is None:
        raise RuntimeError("Processor not initialized — call init_processor() first")
    return _processor
