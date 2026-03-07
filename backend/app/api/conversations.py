from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.session import get_session, get_session_factory
from app.models.conversation import (
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationResponse,
    MessageResponse,
    SendMessageRequest,
)
from app.services import conversation_service
from app.services.conversation_service import AgentError

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph

logger = logging.getLogger(__name__)

STREAM_CHUNK_SIZE = 6

router = APIRouter(prefix="/api", tags=["conversations"])

_agent_graph: CompiledStateGraph | None = None


def init_agent(graph: CompiledStateGraph) -> None:
    global _agent_graph
    _agent_graph = graph


def get_agent() -> CompiledStateGraph:
    if _agent_graph is None:
        raise RuntimeError("Agent not initialized — call init_agent() first")
    return _agent_graph


@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    session: AsyncSession = Depends(get_session),
) -> ConversationResponse:
    result = await conversation_service.create_conversation(session)
    logger.info("Created conversation %s", result.id)
    return result


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> ConversationListResponse:
    conversations, total = await conversation_service.list_conversations(
        session, limit=limit, offset=offset,
    )
    return ConversationListResponse(conversations=conversations, total=total)


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
)
async def get_conversation(
    conversation_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> ConversationDetailResponse:
    detail = await conversation_service.get_conversation_with_messages(
        str(conversation_id), session
    )
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return detail


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_conversation(
    conversation_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> None:
    deleted = await conversation_service.delete_conversation(
        str(conversation_id), session
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    logger.info("Deleted conversation %s", conversation_id)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    conversation_id: UUID,
    request: SendMessageRequest,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    agent: CompiledStateGraph = Depends(get_agent),
) -> MessageResponse:
    conversation = await conversation_service.get_conversation(
        str(conversation_id), session
    )
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    cid = str(conversation_id)
    logger.info("Message received for conversation %s (%d chars)", cid, len(request.content))

    try:
        return await conversation_service.run_agent_turn(
            conversation_id=cid,
            content=request.content,
            agent=agent,
            session=session,
            max_history_messages=settings.max_history_messages,
        )
    except AgentError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI agent failed to generate a response. Please try again.",
        )


def _sse_event(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _chunk_text(text: str, chunk_size: int = STREAM_CHUNK_SIZE) -> list[str]:
    """Split text into word-groups for simulated token streaming."""
    words = text.split(" ")
    chunks: list[str] = []
    for i in range(0, len(words), chunk_size):
        piece = " ".join(words[i : i + chunk_size])
        if chunks:
            piece = " " + piece
        chunks.append(piece)
    return chunks


async def _stream_response(
    conversation_id: str,
    content: str,
    agent: CompiledStateGraph,
    max_history_messages: int,
) -> AsyncGenerator[str, None]:
    """Async generator that yields SSE events for a chat message.

    Creates its own DB session from the factory rather than using FastAPI DI
    because async generators outlive the request scope -- FastAPI closes its
    dependency-injected session when the endpoint returns, but the SSE body
    is still being streamed to the client.

    NOTE: This is *simulated* streaming -- the agent runs to completion, then
    the response text is chunked into word-groups emitted as content_delta
    events with small delays. Real token-level streaming requires a streaming-
    capable LLM; with mock or Ollama, replace ``agent.ainvoke`` with
    ``agent.astream_events`` and yield deltas as they arrive from the model.
    """
    logger.info("Stream started for conversation %s (%d chars)", conversation_id, len(content))
    session_factory = get_session_factory()

    async with session_factory() as session:
        conversation = await conversation_service.get_conversation(
            conversation_id, session
        )
        if conversation is None:
            logger.warning("Stream aborted: conversation %s not found", conversation_id)
            yield _sse_event("error", {"detail": "Conversation not found"})
            return

        try:
            assistant_message = await conversation_service.run_agent_turn(
                conversation_id=conversation_id,
                content=content,
                agent=agent,
                session=session,
                max_history_messages=max_history_messages,
            )
        except AgentError:
            yield _sse_event("error", {"detail": "The AI agent failed to generate a response."})
            return

    yield _sse_event("message_start", {
        "message_id": assistant_message.id,
        "conversation_id": assistant_message.conversation_id,
    })

    for chunk in _chunk_text(assistant_message.content):
        yield _sse_event("content_delta", {"delta": chunk})
        await asyncio.sleep(0.02)

    sources = [s.model_dump() for s in assistant_message.sources] if assistant_message.sources else []
    yield _sse_event("sources", {"sources": sources})
    yield _sse_event("message_end", {"message_id": assistant_message.id})
    logger.info("Stream completed for conversation %s (message %s)", conversation_id, assistant_message.id)


@router.post("/conversations/{conversation_id}/messages/stream")
async def send_message_stream(
    conversation_id: UUID,
    request: SendMessageRequest,
    settings: Settings = Depends(get_settings),
    agent: CompiledStateGraph = Depends(get_agent),
) -> StreamingResponse:
    return StreamingResponse(
        _stream_response(str(conversation_id), request.content, agent, settings.max_history_messages),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
