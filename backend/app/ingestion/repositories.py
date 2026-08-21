"""
Repository for document chunk persistence and retrieval.

Handles bulk insertion with automatic chunk linking, querying, and status management.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.chunker import ChunkData
from app.ingestion.models import DocumentChunk


class DocumentChunkRepository:
    """
    Asynchronous repository for document chunk persistence and retrieval.

    Manages chunk lifecycle including bulk creation with automatic linking,
    status updates, and multi-tenant isolation via profile_id.
    """

    @staticmethod
    async def bulk_create_chunks(
        session: AsyncSession,
        chunks_data: List[ChunkData],
        document_id: UUID,
        profile_id: UUID,
        version: int = 1,
    ) -> List[DocumentChunk]:
        """
        Persist multiple chunks for a document with automatic linking.

        Creates DocumentChunk records for all provided ChunkData objects,
        then automatically links them in sequence via previous_chunk_id and
        next_chunk_id foreign keys.

        Args:
            session: Active async database session.
            chunks_data: List of ChunkData objects from TextChunker.
            document_id: UUID of parent document.
            profile_id: UUID of document owner (for multi-tenant isolation).
            version: Document version number (default 1).

        Returns:
            List of persisted DocumentChunk objects in order.

        Raises:
            Exception: If bulk insertion fails.
        """
        if not chunks_data:
            return []

        chunk_records: List[DocumentChunk] = []

        # Step 1: Create DocumentChunk records without linking
        for chunk_data in chunks_data:
            chunk_record = DocumentChunk(
                document_id=document_id,
                profile_id=profile_id,
                chunk_index=chunk_data.chunk_index,
                chunk_text=chunk_data.chunk_text,
                token_count=chunk_data.token_count,
                overlap_tokens=chunk_data.overlap_tokens,
                start_character=chunk_data.start_character,
                end_character=chunk_data.end_character,
                version=version,
                embedding_status="pending",
            )
            chunk_records.append(chunk_record)
            session.add(chunk_record)

        # Flush to assign IDs without committing
        await session.flush()

        # Step 2: Link chunks in sequence
        for i in range(len(chunk_records)):
            if i > 0:
                chunk_records[i].previous_chunk_id = chunk_records[i - 1].id
            if i < len(chunk_records) - 1:
                chunk_records[i].next_chunk_id = chunk_records[i + 1].id

        # Flush linking updates
        await session.flush()

        return chunk_records

    @staticmethod
    async def get_chunks_by_document(
        session: AsyncSession,
        document_id: UUID,
        profile_id: UUID,
        version: Optional[int] = None,
    ) -> List[DocumentChunk]:
        """
        Fetch all chunks for a document with strict multi-tenant isolation.

        Retrieves chunks ordered by chunk_index, filtering by document_id,
        profile_id, and optional version.

        Args:
            session: Active async database session.
            document_id: UUID of document.
            profile_id: UUID of document owner (isolation check).
            version: Optional version filter (None = all versions).

        Returns:
            List of DocumentChunk objects ordered by chunk_index.
        """
        query = select(DocumentChunk).where(
            and_(
                DocumentChunk.document_id == document_id,
                DocumentChunk.profile_id == profile_id,
            )
        )

        if version is not None:
            query = query.where(DocumentChunk.version == version)

        query = query.order_by(DocumentChunk.chunk_index)

        result = await session.execute(query)
        return result.scalars().all()

    @staticmethod
    async def update_embedding_status(
        session: AsyncSession,
        chunk_ids: List[UUID],
        status: str,
    ) -> None:
        """
        Update embedding_status for specified chunk IDs.

        Validates status is one of the allowed values before updating.

        Args:
            session: Active async database session.
            chunk_ids: List of chunk IDs to update.
            status: New embedding status ('pending', 'processing', 'ready', 'failed').

        Raises:
            ValueError: If status is not a valid embedding status.
        """
        allowed_statuses = {"pending", "processing", "ready", "failed"}
        if status not in allowed_statuses:
            raise ValueError(
                f"Invalid embedding status: {status}. Must be one of: {', '.join(allowed_statuses)}"
            )

        if not chunk_ids:
            return

        stmt = (
            update(DocumentChunk)
            .where(DocumentChunk.id.in_(chunk_ids))
            .values(embedding_status=status)
        )

        await session.execute(stmt)
        await session.flush()

    @staticmethod
    async def delete_chunks_by_document(
        session: AsyncSession,
        document_id: UUID,
        profile_id: UUID,
    ) -> None:
        """
        Delete all chunks associated with a document.

        Enforces multi-tenant isolation by filtering on both document_id
        and profile_id before deletion.

        Args:
            session: Active async database session.
            document_id: UUID of document.
            profile_id: UUID of document owner (isolation check).
        """
        stmt = delete(DocumentChunk).where(
            and_(
                DocumentChunk.document_id == document_id,
                DocumentChunk.profile_id == profile_id,
            )
        )

        await session.execute(stmt)
        await session.flush()
