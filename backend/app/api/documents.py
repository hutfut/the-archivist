import logging
from pathlib import PurePosixPath
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.session import get_session
from app.models.document import DocumentListResponse, DocumentResponse
from app.services import document_service
from app.services.processing import DocumentProcessor, get_processor

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
            file.filename, len(content), max_mb,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large ({len(content)} bytes). Maximum is {max_mb:.0f} MB.",
        )

    result = await document_service.save_document(
        file.filename or "unnamed", content, session, settings, processor,
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
    deleted = await document_service.delete_document(str(document_id), session, settings)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    logger.info("Deleted document %s", document_id)
