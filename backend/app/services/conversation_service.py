from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from app.db.models import Conversation, Message
from app.models.conversation import (
    ConversationDetailResponse,
    ConversationResponse,
    MessageResponse,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

MAX_TITLE_LENGTH = 100


async def create_conversation(session: AsyncSession) -> ConversationResponse:
    now = datetime.now(timezone.utc)
    conversation = Conversation(
        id=str(uuid.uuid4()),
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
) -> list[ConversationResponse]:
    result = await session.execute(
        select(Conversation).order_by(Conversation.updated_at.desc())
    )
    rows = result.scalars().all()
    return [ConversationResponse.model_validate(row) for row in rows]


async def get_conversation(
    conversation_id: str, session: AsyncSession
) -> Conversation | None:
    result = await session.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    return result.scalar_one_or_none()


async def get_conversation_with_messages(
    conversation_id: str, session: AsyncSession
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
    conversation_id: str, session: AsyncSession
) -> bool:
    conversation = await get_conversation(conversation_id, session)
    if conversation is None:
        return False

    await session.delete(conversation)
    await session.commit()
    logger.info("Deleted conversation %s", conversation_id)
    return True


async def add_message(
    conversation_id: str,
    role: str,
    content: str,
    session: AsyncSession,
    sources: list[dict[str, Any]] | None = None,
) -> MessageResponse:
    now = datetime.now(timezone.utc)
    message = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        role=role,
        content=content,
        sources=sources,
        created_at=now,
    )
    session.add(message)

    # Update conversation's updated_at timestamp
    conversation = await get_conversation(conversation_id, session)
    if conversation is not None:
        conversation.updated_at = now

    await session.commit()
    await session.refresh(message)
    return MessageResponse.model_validate(message)


async def set_conversation_title(
    conversation_id: str, title: str, session: AsyncSession
) -> None:
    conversation = await get_conversation(conversation_id, session)
    if conversation is not None and conversation.title is None:
        conversation.title = title[:MAX_TITLE_LENGTH]
        await session.commit()


async def get_conversation_history(
    conversation_id: str, session: AsyncSession
) -> list[dict[str, str]]:
    """Load conversation messages as simple dicts for the agent."""
    result = await session.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()
    return [{"role": m.role, "content": m.content} for m in messages]
