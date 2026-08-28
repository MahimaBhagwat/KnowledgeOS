from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NoteCreate(BaseModel):
    title: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    folder_id: Optional[UUID] = None


class NoteOut(BaseModel):
    id: UUID
    profile_id: UUID
    title: str
    content: str
    folder_id: Optional[UUID] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
