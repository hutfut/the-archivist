import logging
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import PurePosixPath

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import EXTENSION_TO_CONTENT_TYPE, Settings
from app.db.models import Document
from app.models.document import DocumentResponse
from app.services.processing import DocumentProcessor

logger = logging.getLogger(__name__)


def _resolve_content_type(filename: str) -> str:
    """Derive MIME type from file extension rather than trusting client headers."""
    ext = PurePosixPath(filename).suffix.lower()
    return EXTENSION_TO_CONTENT_TYPE.get(ext, "application/octet-stream")


async def save_document(
    file: UploadFile,
    session: AsyncSession,
    settings: Settings,
    processor: DocumentProcessor,
) -> DocumentResponse:
    """Persist an uploaded file to disk, process it, and record metadata."""
    doc_id = str(uuid.uuid4())
    filename = file.filename or "unnamed"
    content_type = _resolve_content_type(filename)

    doc_dir = settings.upload_dir / doc_id
    doc_dir.mkdir(parents=True, exist_ok=True)
    file_path = doc_dir / filename

    content = await file.read()
    file_path.write_bytes(content)

    now = datetime.now(timezone.utc)
    doc = Document(
        id=doc_id,
        filename=filename,
        content_type=content_type,
        file_size=len(content),
        chunk_count=0,
        created_at=now,
    )
    session.add(doc)
    await session.flush()

    chunk_count = await processor.process(
        doc_id, file_path, content_type, session, filename=filename,
    )
    doc.chunk_count = chunk_count

    await session.commit()
    await session.refresh(doc)

    logger.info(
        "Saved document %s (%s, %d bytes, %d chunks)",
        doc_id, filename, len(content), chunk_count,
    )
    return DocumentResponse.model_validate(doc)


async def list_documents(
    session: AsyncSession,
    limit: int = 50,
    offset: int = 0,
) -> list[DocumentResponse]:
    """Return documents ordered by creation time (newest first)."""
    stmt = (
        select(Document)
        .order_by(Document.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [DocumentResponse.model_validate(row) for row in rows]


async def get_document(
    document_id: str, session: AsyncSession
) -> Document | None:
    """Fetch a single document by ID, or None if not found."""
    result = await session.execute(
        select(Document).where(Document.id == document_id)
    )
    return result.scalar_one_or_none()


async def delete_document(
    document_id: str,
    session: AsyncSession,
    settings: Settings,
) -> bool:
    """Delete a document's file, chunks (via CASCADE), and metadata."""
    doc = await get_document(document_id, session)
    if doc is None:
        return False

    await session.delete(doc)
    await session.commit()

    doc_dir = settings.upload_dir / document_id
    if doc_dir.exists():
        shutil.rmtree(doc_dir)

    logger.info("Deleted document %s (%s)", document_id, doc.filename)
    return True
