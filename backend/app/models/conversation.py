import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SourceAttribution(BaseModel):
    document_id: uuid.UUID
    filename: str
    chunk_content: str
    similarity_score: float
    section_heading: str | None = None


class MessageResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    sources: list[SourceAttribution] | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationResponse(BaseModel):
    id: uuid.UUID
    title: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationListResponse(BaseModel):
    conversations: list[ConversationResponse]
    total: int


class ConversationDetailResponse(ConversationResponse):
    messages: list[MessageResponse] = Field(default_factory=list)


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
