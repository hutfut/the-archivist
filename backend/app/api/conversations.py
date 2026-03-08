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
        session,
        limit=limit,
        offset=offset,
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
    detail = await conversation_service.get_conversation_with_messages(conversation_id, session)
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
    deleted = await conversation_service.delete_conversation(conversation_id, session)
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
    conversation = await conversation_service.get_conversation(conversation_id, session)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    logger.info(
        "Message received for conversation %s (%d chars)", conversation_id, len(request.content)
    )

    try:
        return await conversation_service.run_agent_turn(
            conversation_id=conversation_id,
            content=request.content,
            agent=agent,
            session=session,
            max_history_messages=settings.max_history_messages,
        )
    except AgentError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI agent failed to generate a response. Please try again.",
        ) from None


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


async def _stream_response_simulated(
    conversation_id: UUID,
    content: str,
    agent: CompiledStateGraph,
    max_history_messages: int,
) -> AsyncGenerator[str, None]:
    """Simulated streaming for mock provider: run agent to completion, then
    chunk the response into word-groups emitted as SSE content_delta events."""
    session_factory = get_session_factory()

    async with session_factory() as session:
        conversation = await conversation_service.get_conversation(conversation_id, session)
        if conversation is None:
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

    msg_id = str(assistant_message.id)
    yield _sse_event(
        "message_start",
        {"message_id": msg_id, "conversation_id": str(assistant_message.conversation_id)},
    )

    for chunk in _chunk_text(assistant_message.content):
        yield _sse_event("content_delta", {"delta": chunk})
        await asyncio.sleep(0.02)

    sources = (
        [s.model_dump(mode="json") for s in assistant_message.sources]
        if assistant_message.sources
        else []
    )
    yield _sse_event("sources", {"sources": sources})
    yield _sse_event("message_end", {"message_id": msg_id})


async def _stream_response_real(
    conversation_id: UUID,
    content: str,
    agent: CompiledStateGraph,
    max_history_messages: int,
) -> AsyncGenerator[str, None]:
    """Real token streaming for LLM providers that support it (Anthropic, Ollama).

    Uses astream_events to yield token deltas as the model generates them.
    Persists both messages after streaming completes.
    """
    session_factory = get_session_factory()

    async with session_factory() as session:
        conversation = await conversation_service.get_conversation(conversation_id, session)
        if conversation is None:
            yield _sse_event("error", {"detail": "Conversation not found"})
            return

        await conversation_service.add_message(
            conversation_id=conversation_id,
            role="user",
            content=content,
            session=session,
            commit=False,
        )

        history = await conversation_service.get_conversation_history(
            conversation_id, session, max_messages=max_history_messages
        )

        yield _sse_event(
            "message_start",
            {"message_id": "", "conversation_id": str(conversation_id)},
        )

        full_response = ""
        sources: list[dict[str, Any]] = []
        started_generating = False

        try:
            async for event in agent.astream_events(
                {"query": content, "conversation_history": history},
                version="v2",
            ):
                kind = event.get("event", "")

                if kind == "on_chat_model_stream":
                    node = event.get("metadata", {}).get("langgraph_node")
                    if node != "generate_response":
                        continue
                    chunk = event.get("data", {}).get("chunk")
                    if chunk is not None:
                        token = str(chunk.content) if hasattr(chunk, "content") else ""
                        if token:
                            if not started_generating:
                                started_generating = True
                            full_response += token
                            yield _sse_event("content_delta", {"delta": token})

                elif kind == "on_chain_end" and event.get("name") == "generate_response":
                    output = event.get("data", {}).get("output", {})
                    sources = output.get("sources", [])

        except Exception:
            logger.exception("Agent stream failed for conversation %s", conversation_id)
            await session.rollback()
            yield _sse_event("error", {"detail": "The AI agent failed to generate a response."})
            return

        if not full_response:
            graph_result = None
            try:
                graph_result = await agent.ainvoke(
                    {"query": content, "conversation_history": history}
                )
            except Exception:
                logger.exception("Agent fallback failed for conversation %s", conversation_id)
                await session.rollback()
                yield _sse_event(
                    "error", {"detail": "The AI agent failed to generate a response."}
                )
                return

            full_response = graph_result.get("response", "")
            sources = graph_result.get("sources", [])
            for chunk in _chunk_text(full_response):
                yield _sse_event("content_delta", {"delta": chunk})
                await asyncio.sleep(0.02)

        assistant_message = await conversation_service.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=full_response,
            session=session,
            sources=sources or None,
            commit=False,
        )

        await conversation_service.set_conversation_title(
            conversation_id, content, session, commit=False
        )
        await session.commit()

    msg_id = str(assistant_message.id)
    sources_json = (
        [s.model_dump(mode="json") for s in assistant_message.sources]
        if assistant_message.sources
        else []
    )
    yield _sse_event("sources", {"sources": sources_json})
    yield _sse_event("message_end", {"message_id": msg_id})


async def _stream_response(
    conversation_id: UUID,
    content: str,
    agent: CompiledStateGraph,
    max_history_messages: int,
    llm_provider: str,
) -> AsyncGenerator[str, None]:
    """Route to the appropriate streaming implementation based on LLM provider."""
    logger.info(
        "Stream started for conversation %s (%d chars, provider=%s)",
        conversation_id,
        len(content),
        llm_provider,
    )

    if llm_provider == "mock":
        gen = _stream_response_simulated(
            conversation_id, content, agent, max_history_messages
        )
    else:
        gen = _stream_response_real(
            conversation_id, content, agent, max_history_messages
        )

    async for event in gen:
        yield event

    logger.info("Stream completed for conversation %s", conversation_id)


@router.post("/conversations/{conversation_id}/messages/stream")
async def send_message_stream(
    conversation_id: UUID,
    request: SendMessageRequest,
    settings: Settings = Depends(get_settings),
    agent: CompiledStateGraph = Depends(get_agent),
) -> StreamingResponse:
    return StreamingResponse(
        _stream_response(
            conversation_id,
            request.content,
            agent,
            settings.max_history_messages,
            settings.llm_provider,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
