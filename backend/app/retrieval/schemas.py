from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.retrieval.retriever import RetrieverContext


class SearchQueryRequest(BaseModel):
    """Request payload for semantic search."""

    query: str = Field(..., min_length=1)
    folder_id: Optional[UUID] = None
    top_k: int = Field(5, gt=0)
    score_threshold: float = Field(0.0, ge=0.0)

    model_config = ConfigDict(from_attributes=True)

    @field_validator("query", mode="before")
    @classmethod
    def _strip_query(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("query")
    @classmethod
    def _validate_query(cls, value: str) -> str:
        if not value:
            raise ValueError("query must not be empty")
        return value


class SearchQueryResponse(BaseModel):
    """Response payload for semantic search."""

    contexts: List[RetrieverContext]
    formatted_prompt_context: str

    model_config = ConfigDict(from_attributes=True)


__all__ = ["SearchQueryRequest", "SearchQueryResponse"]

