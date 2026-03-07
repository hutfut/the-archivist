from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, status
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
    session: AsyncSession = Depends(get_session),
) -> ConversationListResponse:
    conversations = await conversation_service.list_conversations(session)
    return ConversationListResponse(conversations=conversations)


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
)
async def get_conversation(
    conversation_id: str,
    session: AsyncSession = Depends(get_session),
) -> ConversationDetailResponse:
    detail = await conversation_service.get_conversation_with_messages(
        conversation_id, session
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
    conversation_id: str,
    session: AsyncSession = Depends(get_session),
) -> None:
    deleted = await conversation_service.delete_conversation(
        conversation_id, session
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
    conversation_id: str,
    request: SendMessageRequest,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    agent: CompiledStateGraph = Depends(get_agent),
) -> MessageResponse:
    conversation = await conversation_service.get_conversation(
        conversation_id, session
    )
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    logger.info("Message received for conversation %s (%d chars)", conversation_id, len(request.content))

    await conversation_service.add_message(
        conversation_id=conversation_id,
        role="user",
        content=request.content,
        session=session,
    )

    history = await conversation_service.get_conversation_history(
        conversation_id, session, max_messages=settings.max_history_messages,
    )

    agent_result = await agent.ainvoke({
        "query": request.content,
        "conversation_history": history,
    })

    assistant_message = await conversation_service.add_message(
        conversation_id=conversation_id,
        role="assistant",
        content=agent_result["response"],
        session=session,
        sources=agent_result.get("sources"),
    )

    await conversation_service.set_conversation_title(
        conversation_id, request.content, session
    )

    return assistant_message


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
    """Async generator that yields SSE events for a chat message."""
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

        await conversation_service.add_message(
            conversation_id=conversation_id,
            role="user",
            content=content,
            session=session,
        )

        history = await conversation_service.get_conversation_history(
            conversation_id, session, max_messages=max_history_messages,
        )

    agent_result = await agent.ainvoke({
        "query": content,
        "conversation_history": history,
    })

    response_text: str = agent_result["response"]
    sources: list[dict[str, Any]] = agent_result.get("sources", [])

    async with session_factory() as session:
        assistant_message = await conversation_service.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=response_text,
            session=session,
            sources=sources,
        )

        await conversation_service.set_conversation_title(
            conversation_id, content, session
        )

    yield _sse_event("message_start", {
        "message_id": assistant_message.id,
        "conversation_id": assistant_message.conversation_id,
    })

    for chunk in _chunk_text(response_text):
        yield _sse_event("content_delta", {"delta": chunk})
        await asyncio.sleep(0.02)

    yield _sse_event("sources", {"sources": sources})
    yield _sse_event("message_end", {"message_id": assistant_message.id})
    logger.info("Stream completed for conversation %s (message %s)", conversation_id, assistant_message.id)


@router.post("/conversations/{conversation_id}/messages/stream")
async def send_message_stream(
    conversation_id: str,
    request: SendMessageRequest,
    settings: Settings = Depends(get_settings),
    agent: CompiledStateGraph = Depends(get_agent),
) -> StreamingResponse:
    return StreamingResponse(
        _stream_response(conversation_id, request.content, agent, settings.max_history_messages),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
