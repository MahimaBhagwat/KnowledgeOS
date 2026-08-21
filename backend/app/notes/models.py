from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import DateTime, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Note(Base):
    """Represents a user-authored quick note.

    Notes are tenant-scoped by profile_id and optionally belong to a folder.
    Unlike Documents, notes are plain text authored directly in-app rather
    than uploaded and parsed — no file_path or file_type is needed.
    """

    __tablename__ = "notes"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    folder_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)

    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())