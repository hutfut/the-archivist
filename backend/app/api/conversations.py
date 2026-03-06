from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
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
    return await conversation_service.create_conversation(session)


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


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    conversation_id: str,
    request: SendMessageRequest,
    session: AsyncSession = Depends(get_session),
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

    await conversation_service.add_message(
        conversation_id=conversation_id,
        role="user",
        content=request.content,
        session=session,
    )

    history = await conversation_service.get_conversation_history(
        conversation_id, session
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
