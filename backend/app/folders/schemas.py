from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing_extensions import Literal


FolderType = Literal["uploaded", "quick_notes", "archive", "custom"]


class FolderBase(BaseModel):
    """Base schema for Folder with validation for the `name` field.

    Enforces trimming of whitespace and maximum length of 100 characters.
    """

    name: str = Field(..., max_length=100)

    model_config = ConfigDict(from_attributes=True)

    @field_validator("name", mode="before")
    @classmethod
    def _strip_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not isinstance(v, str):
            # Let Pydantic handle type errors downstream
            return v
        return v.strip()

    @field_validator("name")
    @classmethod
    def _validate_non_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("Folder name must not be empty or whitespace")
        if len(v) > 100:
            # Defensive check; Field(max_length=100) should already enforce this.
            raise ValueError("Folder name must be at most 100 characters")
        return v


class FolderCreate(FolderBase):
    """Schema used when creating a new folder."""


class FolderUpdate(BaseModel):
    """Schema for partial updates to a folder."""

    name: Optional[str] = Field(None, max_length=100)

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
    def _validate_non_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not v:
            raise ValueError("Folder name must not be empty or whitespace")
        if len(v) > 100:
            raise ValueError("Folder name must be at most 100 characters")
        return v


class FolderInDB(BaseModel):
    id: UUID
    profile_id: UUID
    name: str
    folder_type: FolderType
    is_system_folder: bool = False
    document_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FolderOut(FolderInDB):
    """Response schema for folder resources."""


__all__ = [
    "FolderBase",
    "FolderCreate",
    "FolderUpdate",
    "FolderInDB",
    "FolderOut",
    "FolderType",
]
