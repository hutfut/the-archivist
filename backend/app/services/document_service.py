import logging
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import PurePosixPath

from sqlalchemy import func, select
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
    filename: str,
    content: bytes,
    session: AsyncSession,
    settings: Settings,
    processor: DocumentProcessor,
) -> DocumentResponse:
    """Persist uploaded file bytes to disk, process them, and record metadata."""
    doc_id = uuid.uuid4()
    content_type = _resolve_content_type(filename)

    doc_dir = settings.upload_dir / str(doc_id)
    doc_dir.mkdir(parents=True, exist_ok=True)
    file_path = doc_dir / filename

    file_path.write_bytes(content)

    now = datetime.now(UTC)
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
        doc_id,
        file_path,
        content_type,
        session,
        filename=filename,
    )
    doc.chunk_count = chunk_count

    await session.commit()
    await session.refresh(doc)

    logger.info(
        "Saved document %s (%s, %d bytes, %d chunks)",
        doc_id,
        filename,
        len(content),
        chunk_count,
    )
    return DocumentResponse.model_validate(doc)


async def list_documents(
    session: AsyncSession,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[DocumentResponse], int]:
    """Return documents ordered by creation time (newest first) and total count."""
    stmt = select(Document).order_by(Document.created_at.desc()).limit(limit).offset(offset)
    result = await session.execute(stmt)
    rows = result.scalars().all()

    count_result = await session.execute(select(func.count()).select_from(Document))
    total = count_result.scalar_one()

    return [DocumentResponse.model_validate(row) for row in rows], total


async def get_document(document_id: uuid.UUID, session: AsyncSession) -> Document | None:
    """Fetch a single document by ID, or None if not found."""
    result = await session.execute(select(Document).where(Document.id == document_id))
    return result.scalar_one_or_none()


async def delete_document(
    document_id: uuid.UUID,
    session: AsyncSession,
    settings: Settings,
) -> bool:
    """Delete a document's file, chunks (via CASCADE), and metadata."""
    doc = await get_document(document_id, session)
    if doc is None:
        return False

    await session.delete(doc)
    await session.commit()

    doc_dir = settings.upload_dir / str(document_id)
    try:
        if doc_dir.exists():
            shutil.rmtree(doc_dir)
    except OSError:
        logger.warning("Failed to remove file directory for document %s", document_id)

    logger.info("Deleted document %s (%s)", document_id, doc.filename)
    return True
