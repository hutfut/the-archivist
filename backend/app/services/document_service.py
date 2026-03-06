import logging
import shutil
import uuid
from datetime import datetime, timezone

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.models import Document
from app.models.document import DocumentResponse

logger = logging.getLogger(__name__)


async def save_document(
    file: UploadFile,
    session: AsyncSession,
    settings: Settings,
) -> DocumentResponse:
    """Persist an uploaded file to disk and record metadata in the database."""
    doc_id = str(uuid.uuid4())
    filename = file.filename or "unnamed"

    doc_dir = settings.upload_dir / doc_id
    doc_dir.mkdir(parents=True, exist_ok=True)
    file_path = doc_dir / filename

    content = await file.read()
    file_path.write_bytes(content)

    now = datetime.now(timezone.utc)
    doc = Document(
        id=doc_id,
        filename=filename,
        content_type=file.content_type or "application/octet-stream",
        file_size=len(content),
        chunk_count=0,
        created_at=now,
    )
    session.add(doc)
    await session.commit()
    await session.refresh(doc)

    logger.info("Saved document %s (%s, %d bytes)", doc_id, filename, len(content))
    return DocumentResponse.model_validate(doc)


async def list_documents(session: AsyncSession) -> list[DocumentResponse]:
    """Return all documents ordered by creation time (newest first)."""
    result = await session.execute(
        select(Document).order_by(Document.created_at.desc())
    )
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
    """Delete a document's file and metadata. Returns True if found and deleted."""
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
