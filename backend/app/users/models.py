from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Boolean, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Profile(Base):
    """Represents a user profile in the application.

    Matches the documented `profiles` table schema.
    """

    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # One-to-one relationship to user preferences
    preference: Mapped[Optional["UserPreference"]] = relationship(
        "UserPreference",
        back_populates="profile",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"<Profile id={self.id} email={self.email}>"


class UserPreference(Base):
    """Per-profile user preferences and feature toggles.

    Matches the documented `user_preferences` table schema with a strict
    one-to-one mapping to profiles.profile_id.
    """

    __tablename__ = "user_preferences"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    # Appearance
    theme: Mapped[str] = mapped_column(String(32), nullable=False, default="light")

    # AI pipeline toggles
    streaming_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    planner_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    reviewer_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Timestamps
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    profile: Mapped[Profile] = relationship("Profile", back_populates="preference", uselist=False)

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"<UserPreference id={self.id} profile_id={self.profile_id}>"
