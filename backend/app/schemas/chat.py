from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from backend.app.schemas.answers import AnswerCitation
from backend.app.schemas.ask import AskResponse
from backend.app.schemas.retrieval import RetrievalRequestBase


class ChatSessionCreate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    collection_id: int | None = None

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class ChatSessionResponse(BaseModel):
    id: int
    title: str | None
    collection_id: int | None
    created_at: datetime
    updated_at: datetime


class ChatMessageResponse(BaseModel):
    id: int
    session_id: int
    role: Literal["user", "assistant"]
    content: str
    citations: list[AnswerCitation]
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ChatSessionMessagesResponse(BaseModel):
    session: ChatSessionResponse
    messages: list[ChatMessageResponse]


class SessionAskRequest(RetrievalRequestBase):
    top_k: int = Field(default=5, ge=1, le=20)


class SessionAskResponse(AskResponse):
    session_id: int
    user_message_id: int
    assistant_message_id: int
