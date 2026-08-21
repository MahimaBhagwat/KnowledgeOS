from __future__ import annotations

from typing import List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Flashcard(BaseModel):
    question: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)

    model_config = ConfigDict(from_attributes=True)


class DocumentInsightsResponse(BaseModel):
    document_id: UUID
    summary: str
    key_takeaways: List[str]
    flashcards: List[Flashcard]

    model_config = ConfigDict(from_attributes=True)
