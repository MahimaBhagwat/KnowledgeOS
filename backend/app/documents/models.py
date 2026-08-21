from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Document(Base):
    """Represents a user-uploaded document with metadata and processing state.

    Documents are tenant-scoped by profile_id and belong to exactly one folder.
    A UniqueConstraint on (folder_id, name) prevents duplicate file names
    within the same folder while allowing different folders to have files
    with identical names.

    Supports soft-delete (is_deleted flag) and version tracking for processing
    and update workflows.
    """

    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("folder_id", "name", name="uq_documents_folder_id_name"),)

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    folder_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(2048), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)

    is_favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"<Document id={self.id} profile_id={self.profile_id} folder_id={self.folder_id} name={self.name}>"
