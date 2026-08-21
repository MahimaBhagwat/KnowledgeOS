from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from typing import Literal


class CitationOut(BaseModel):
    """Representation of a cited document chunk included with an assistant response."""

    chunk_id: UUID
    document_id: UUID
    chunk_index: int
    similarity_score: float
    chunk_text: str


class ChatMessageCreate(BaseModel):
    """Payload for creating/sending a user message in a chat session."""

    content: str = Field(..., min_length=1)
    folder_id: Optional[UUID] = None
    top_k: Optional[int] = Field(5, gt=0)


class ChatMessageOut(BaseModel):
    """Read representation of a stored chat message."""

    id: UUID
    session_id: UUID
    role: Literal["user", "assistant", "system"]
    content: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    citations: Optional[List[CitationOut]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatSessionCreate(BaseModel):
    """Payload to create a new chat session."""

    title: Optional[str] = Field("New Chat", max_length=255)


class ChatSessionUpdate(BaseModel):
    """Payload to update chat session metadata."""

    title: Optional[str] = Field(None, min_length=1, max_length=255)


class ChatSessionOut(BaseModel):
    """Read representation of a chat session and its messages."""

    id: UUID
    profile_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    messages: Optional[List[ChatMessageOut]] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
