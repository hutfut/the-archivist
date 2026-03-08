import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    id: uuid.UUID
    filename: str
    content_type: str
    file_size: int
    chunk_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int


def filename_to_title(filename: str) -> str:
    """Derive a human-readable title from a filename.

    'Life.md' -> 'Life', 'quarterly_report.pdf' -> 'Quarterly Report'
    """
    without_ext = re.sub(r"\.[^.]+$", "", filename)
    return re.sub(r"[-_]+", " ", without_ext).strip().title()


class DocumentContentResponse(BaseModel):
    id: uuid.UUID
    filename: str
    title: str
    content: str
    content_type: str
    chunk_count: int
    file_size: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SearchResultItem(BaseModel):
    document_id: uuid.UUID
    filename: str
    title: str
    section_heading: str | None
    snippet: str
    score: float


class SearchResponse(BaseModel):
    results: list[SearchResultItem]
    total: int
    query: str


class RelatedDocumentItem(BaseModel):
    id: uuid.UUID
    filename: str
    title: str
    score: float


class RelatedDocumentsResponse(BaseModel):
    documents: list[RelatedDocumentItem]
