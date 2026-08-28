from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

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

    chunks: Mapped[List["NoteChunk"]] = relationship(
        "NoteChunk",
        back_populates="note",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class NoteChunk(Base):
    """Represents a single chunk of a user note for semantic search & RAG."""

    __tablename__ = "note_chunks"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    note_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("notes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    overlap_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    start_character: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    end_character: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    previous_chunk_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("note_chunks.id", ondelete="SET NULL"),
        nullable=True,
    )
    next_chunk_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("note_chunks.id", ondelete="SET NULL"),
        nullable=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    embedding_status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")

    note: Mapped["Note"] = relationship("Note", back_populates="chunks")


__all__ = ["Note", "NoteChunk"]
