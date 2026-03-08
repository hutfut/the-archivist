import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.document import (
    SearchResponse,
    SearchResultItem,
    filename_to_title,
)
from app.services.retrieval import RetrievalService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["search"])

_retrieval_service: RetrievalService | None = None


def init_search(retrieval_service: RetrievalService) -> None:
    global _retrieval_service
    _retrieval_service = retrieval_service


def get_retrieval_service() -> RetrievalService:
    if _retrieval_service is None:
        raise RuntimeError("Search not initialized — call init_search() first")
    return _retrieval_service


@router.get("/search", response_model=SearchResponse)
async def search_documents(
    q: Annotated[str, Query(min_length=1, max_length=500)],
    limit: int = Query(default=10, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
    retrieval: RetrievalService = Depends(get_retrieval_service),
) -> SearchResponse:
    chunks = await retrieval.search(
        query=q,
        session=session,
        top_k=limit + offset,
        candidate_k=max(20, (limit + offset) * 3),
    )

    seen_docs: dict[str, SearchResultItem] = {}
    for chunk in chunks:
        doc_key = str(chunk.document_id)
        if doc_key not in seen_docs:
            snippet = chunk.chunk_content[:300].strip()
            if len(chunk.chunk_content) > 300:
                snippet += "..."
            seen_docs[doc_key] = SearchResultItem(
                document_id=chunk.document_id,
                filename=chunk.filename,
                title=filename_to_title(chunk.filename),
                section_heading=chunk.section_heading,
                snippet=snippet,
                score=chunk.similarity_score,
            )

    all_results = list(seen_docs.values())
    paginated = all_results[offset : offset + limit]

    logger.info("Search for %r returned %d results", q, len(paginated))
    return SearchResponse(
        results=paginated,
        total=len(all_results),
        query=q,
    )
