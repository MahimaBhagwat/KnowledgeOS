from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing_extensions import Literal


class _ModelConfig:
    model_config = ConfigDict(from_attributes=True)


# Profile schemas
class ProfileBase(BaseModel):
    email: EmailStr = Field(..., max_length=320)
    name: Optional[str] = Field(None, max_length=255)
    avatar_url: Optional[str] = Field(None, max_length=2048)


class ProfileCreate(ProfileBase):
    """Payload used when creating a new profile."""
    id: Optional[UUID] = Field(None, description="Explicit UUID matching Supabase Auth user ID")

class ProfileUpdate(BaseModel):
    """Payload used when updating a profile. All fields optional."""

    name: Optional[str] = Field(None, max_length=255)
    avatar_url: Optional[str] = Field(None, max_length=2048)

    model_config = ConfigDict(from_attributes=True)


class ProfileInDB(ProfileBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProfileOut(ProfileInDB):
    pass


# UserPreference schemas
ThemeLiteral = Literal["light", "dark"]


class UserPreferenceBase(BaseModel):
    theme: ThemeLiteral = Field("light")
    streaming_enabled: bool = Field(False)
    planner_enabled: bool = Field(True)
    reviewer_enabled: bool = Field(True)

    model_config = ConfigDict(from_attributes=True)


class UserPreferenceCreate(UserPreferenceBase):
    profile_id: UUID


class UserPreferenceUpdate(BaseModel):
    theme: Optional[ThemeLiteral] = None
    streaming_enabled: Optional[bool] = None
    planner_enabled: Optional[bool] = None
    reviewer_enabled: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)


class UserPreferenceInDB(UserPreferenceBase):
    id: UUID
    profile_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserPreferenceOut(UserPreferenceInDB):
    pass


__all__ = [
    "ProfileBase",
    "ProfileCreate",
    "ProfileUpdate",
    "ProfileInDB",
    "ProfileOut",
    "UserPreferenceBase",
    "UserPreferenceCreate",
    "UserPreferenceUpdate",
    "UserPreferenceInDB",
    "UserPreferenceOut",
]
