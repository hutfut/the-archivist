from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select

from app.db.models import Conversation, Message
from app.models.conversation import (
    ConversationDetailResponse,
    ConversationResponse,
    MessageResponse,
)

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

MAX_TITLE_LENGTH = 100


class AgentError(Exception):
    """Raised when the AI agent fails during a conversation turn."""


async def create_conversation(session: AsyncSession) -> ConversationResponse:
    now = datetime.now(timezone.utc)
    conversation = Conversation(
        id=uuid.uuid4(),
        title=None,
        created_at=now,
        updated_at=now,
    )
    session.add(conversation)
    await session.commit()
    await session.refresh(conversation)
    logger.info("Created conversation %s", conversation.id)
    return ConversationResponse.model_validate(conversation)


async def list_conversations(
    session: AsyncSession,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[ConversationResponse], int]:
    stmt = (
        select(Conversation)
        .order_by(Conversation.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    rows = result.scalars().all()

    count_result = await session.execute(select(func.count()).select_from(Conversation))
    total = count_result.scalar_one()

    return [ConversationResponse.model_validate(row) for row in rows], total


async def get_conversation(
    conversation_id: uuid.UUID, session: AsyncSession
) -> Conversation | None:
    result = await session.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    return result.scalar_one_or_none()


async def get_conversation_with_messages(
    conversation_id: uuid.UUID, session: AsyncSession
) -> ConversationDetailResponse | None:
    conversation = await get_conversation(conversation_id, session)
    if conversation is None:
        return None

    result = await session.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()

    return ConversationDetailResponse(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[MessageResponse.model_validate(m) for m in messages],
    )


async def delete_conversation(
    conversation_id: uuid.UUID, session: AsyncSession
) -> bool:
    conversation = await get_conversation(conversation_id, session)
    if conversation is None:
        return False

    await session.delete(conversation)
    await session.commit()
    logger.info("Deleted conversation %s", conversation_id)
    return True


async def add_message(
    conversation_id: uuid.UUID,
    role: str,
    content: str,
    session: AsyncSession,
    sources: list[dict[str, Any]] | None = None,
    commit: bool = True,
) -> MessageResponse:
    now = datetime.now(timezone.utc)
    message = Message(
        id=uuid.uuid4(),
        conversation_id=conversation_id,
        role=role,
        content=content,
        sources=sources,
        created_at=now,
    )
    session.add(message)

    conversation = await get_conversation(conversation_id, session)
    if conversation is not None:
        conversation.updated_at = now

    if commit:
        await session.commit()
        await session.refresh(message)
    else:
        await session.flush()

    return MessageResponse.model_validate(message)


async def set_conversation_title(
    conversation_id: uuid.UUID, title: str, session: AsyncSession,
    commit: bool = True,
) -> None:
    conversation = await get_conversation(conversation_id, session)
    if conversation is not None and conversation.title is None:
        conversation.title = title[:MAX_TITLE_LENGTH]
        if commit:
            await session.commit()


async def get_conversation_history(
    conversation_id: uuid.UUID,
    session: AsyncSession,
    max_messages: int | None = None,
) -> list[dict[str, str]]:
    """Load recent conversation messages as simple dicts for the agent.

    When max_messages is set, only the most recent N messages are returned.
    This prevents unbounded context growth in long conversations.
    """
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
    )
    if max_messages is not None:
        stmt = stmt.limit(max_messages)

    result = await session.execute(stmt)
    messages = list(reversed(result.scalars().all()))
    return [{"role": m.role, "content": m.content} for m in messages]


async def run_agent_turn(
    conversation_id: uuid.UUID,
    content: str,
    agent: CompiledStateGraph,
    session: AsyncSession,
    max_history_messages: int | None = None,
) -> MessageResponse:
    """Execute a full chat turn: save user message, invoke agent, save response.

    All DB writes are committed atomically. On agent failure the session is
    rolled back and AgentError is raised so callers can translate to HTTP 502
    or an SSE error event.
    """
    await add_message(
        conversation_id=conversation_id,
        role="user",
        content=content,
        session=session,
        commit=False,
    )

    history = await get_conversation_history(
        conversation_id, session, max_messages=max_history_messages,
    )

    try:
        agent_result = await agent.ainvoke({
            "query": content,
            "conversation_history": history,
        })
    except Exception:
        logger.exception("Agent failed for conversation %s", conversation_id)
        await session.rollback()
        raise AgentError("The AI agent failed to generate a response.")

    assistant_message = await add_message(
        conversation_id=conversation_id,
        role="assistant",
        content=agent_result["response"],
        session=session,
        sources=agent_result.get("sources"),
        commit=False,
    )

    await set_conversation_title(
        conversation_id, content, session, commit=False,
    )

    await session.commit()
    return assistant_message
