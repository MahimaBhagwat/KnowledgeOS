from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, field_validator


class DocumentTypeEnum(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    PPTX = "pptx"
    MARKDOWN = "markdown"
    TXT = "txt"
    HTML = "html"


class DocumentBase(BaseModel):
    """Base shared document properties and validation."""

    name: str = Field(..., max_length=255)
    file_type: DocumentTypeEnum
    file_size: int = Field(..., ge=0)
    is_favorite: Optional[bool] = Field(False)

    model_config = ConfigDict(from_attributes=True)

    @field_validator("name", mode="before")
    @classmethod
    def _strip_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not isinstance(v, str):
            return v
        return v.strip()

    @field_validator("name")
    @classmethod
    def _validate_name_non_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("Document name must not be empty or whitespace")
        if len(v) > 255:
            raise ValueError("Document name must be at most 255 characters")
        return v


class DocumentCreate(DocumentBase):
    folder_id: UUID
    file_path: str = Field(..., max_length=2048)


class DocumentUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    folder_id: Optional[UUID] = None
    is_favorite: Optional[bool] = None
    is_deleted: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("name", mode="before")
    @classmethod
    def _strip_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not isinstance(v, str):
            return v
        return v.strip()

    @field_validator("name")
    @classmethod
    def _validate_name_optional(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not v:
            raise ValueError("Document name must not be empty or whitespace")
        if len(v) > 255:
            raise ValueError("Document name must be at most 255 characters")
        return v


class DocumentInDBBase(BaseModel):
    id: UUID
    profile_id: UUID
    folder_id: UUID
    name: str
    file_path: str
    file_type: DocumentTypeEnum
    file_size: int
    is_favorite: bool
    is_deleted: bool
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentOut(DocumentInDBBase):
    pass


__all__ = [
    "DocumentTypeEnum",
    "DocumentBase",
    "DocumentCreate",
    "DocumentUpdate",
    "DocumentInDBBase",
    "DocumentOut",
]
