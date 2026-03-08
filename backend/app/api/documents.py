import logging
from pathlib import PurePosixPath
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.models import Chunk, Document
from app.db.session import get_session
from app.models.document import (
    DocumentContentResponse,
    DocumentListResponse,
    DocumentResponse,
    RelatedDocumentItem,
    RelatedDocumentsResponse,
    filename_to_title,
)
from app.services import document_service
from app.services.processing import DocumentProcessor, get_processor
from app.services.text_extraction import extract_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["documents"])


def _validate_upload(file: UploadFile, settings: Settings) -> None:
    """Raise HTTPException if the upload is invalid."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    extension = PurePosixPath(file.filename).suffix.lower()
    if extension not in settings.allowed_extensions:
        allowed = ", ".join(sorted(settings.allowed_extensions))
        logger.warning("Rejected upload: unsupported extension %s (%s)", extension, file.filename)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {extension}. Allowed: {allowed}",
        )


@router.post(
    "/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    processor: DocumentProcessor = Depends(get_processor),
) -> DocumentResponse:
    _validate_upload(file, settings)

    content = await file.read()
    if not content:
        logger.warning("Rejected upload: empty file (%s)", file.filename)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty",
        )

    if len(content) > settings.max_upload_bytes:
        max_mb = settings.max_upload_bytes / (1024 * 1024)
        logger.warning(
            "Rejected upload: %s is %d bytes (max %.0f MB)",
            file.filename,
            len(content),
            max_mb,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large ({len(content)} bytes). Maximum is {max_mb:.0f} MB.",
        )

    result = await document_service.save_document(
        file.filename or "unnamed",
        content,
        session,
        settings,
        processor,
    )
    logger.info("Uploaded document %s (%s, %d bytes)", result.id, result.filename, result.file_size)
    return result


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> DocumentListResponse:
    docs, total = await document_service.list_documents(session, limit=limit, offset=offset)
    return DocumentListResponse(documents=docs, total=total)


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_document(
    document_id: UUID,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> None:
    deleted = await document_service.delete_document(document_id, session, settings)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    logger.info("Deleted document %s", document_id)


@router.get(
    "/documents/{document_id}/content",
    response_model=DocumentContentResponse,
)
async def get_document_content(
    document_id: UUID,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> DocumentContentResponse:
    doc = await document_service.get_document(document_id, session)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    file_path = settings.upload_dir / str(document_id) / doc.filename
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document file not found on disk",
        )

    content = extract_text(file_path, doc.content_type)

    return DocumentContentResponse(
        id=doc.id,
        filename=doc.filename,
        title=filename_to_title(doc.filename),
        content=content,
        content_type=doc.content_type,
        chunk_count=doc.chunk_count,
        file_size=doc.file_size,
        created_at=doc.created_at,
    )


@router.get(
    "/documents/{document_id}/related",
    response_model=RelatedDocumentsResponse,
)
async def get_related_documents(
    document_id: UUID,
    limit: int = Query(default=5, ge=1, le=20),
    session: AsyncSession = Depends(get_session),
) -> RelatedDocumentsResponse:
    doc = await document_service.get_document(document_id, session)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    source_avg = (
        select(func.avg(Chunk.embedding)).where(Chunk.document_id == document_id).scalar_subquery()
    )

    other_avg = (
        select(
            Chunk.document_id,
            func.avg(Chunk.embedding).label("avg_emb"),
        )
        .where(Chunk.document_id != document_id)
        .group_by(Chunk.document_id)
        .subquery()
    )

    distance_expr = other_avg.c.avg_emb.op("<=>")(source_avg)
    similarity = (1 - distance_expr).label("similarity")

    stmt = (
        select(Document.id, Document.filename, similarity)
        .join(other_avg, Document.id == other_avg.c.document_id)
        .where(source_avg.isnot(None))
        .order_by(distance_expr)
        .limit(limit)
    )

    rows = (await session.execute(stmt)).all()
    return RelatedDocumentsResponse(
        documents=[
            RelatedDocumentItem(
                id=row.id,
                filename=row.filename,
                title=filename_to_title(row.filename),
                score=max(0.0, float(row.similarity)),
            )
            for row in rows
        ]
    )
