from datetime import datetime

from pydantic import BaseModel, Field


class SourceAttribution(BaseModel):
    document_id: str
    filename: str
    chunk_content: str
    similarity_score: float


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    sources: list[SourceAttribution] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationResponse(BaseModel):
    id: str
    title: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationListResponse(BaseModel):
    conversations: list[ConversationResponse]


class ConversationDetailResponse(ConversationResponse):
    messages: list[MessageResponse] = Field(default_factory=list)


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
