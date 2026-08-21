"""
SQLAlchemy models for the document ingestion pipeline.

Defines the DocumentChunk model for storing parsed and chunked document content.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
    UUID as SQLAlchemyUUID,
)
from sqlalchemy.sql import func

from app.core.database import Base


class DocumentChunk(Base):
    """
    Represents a single chunk of a parsed document.

    Each document is split into semantic chunks for embedding and retrieval.
    Chunks maintain ordering, overlap information, and embedding status.
    """

    __tablename__ = "document_chunks"

    id = Column(
        SQLAlchemyUUID(as_uuid=True),
        primary_key=True,
        default=func.gen_random_uuid(),
    )
    document_id = Column(
        SQLAlchemyUUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    profile_id = Column(
        SQLAlchemyUUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=False)
    overlap_tokens = Column(Integer, nullable=False, default=0)
    start_character = Column(Integer, nullable=True)
    end_character = Column(Integer, nullable=True)
    previous_chunk_id = Column(
        SQLAlchemyUUID(as_uuid=True),
        ForeignKey("document_chunks.id", ondelete="SET NULL"),
        nullable=True,
    )
    next_chunk_id = Column(
        SQLAlchemyUUID(as_uuid=True),
        ForeignKey("document_chunks.id", ondelete="SET NULL"),
        nullable=True,
    )
    version = Column(Integer, nullable=False, default=1)
    embedding_status = Column(
        String(50),
        nullable=False,
        default="pending",
    )
