from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import Boolean, DateTime, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Folder(Base):
    """Represents a user-owned folder for organizing documents.

    The folders table is tenant-scoped by profile_id. A UniqueConstraint on
    (profile_id, name) prevents duplicate folder names per user while allowing
    different users to have folders with the same name.
    """

    __tablename__ = "folders"
    __table_args__ = (UniqueConstraint("profile_id", "name", name="uq_folders_profile_id_name"),)

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    folder_type: Mapped[str] = mapped_column(String(50), nullable=False, default="custom")
    is_system_folder: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    document_count: int = 0
    

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"<Folder id={self.id} profile_id={self.profile_id} name={self.name}>"
