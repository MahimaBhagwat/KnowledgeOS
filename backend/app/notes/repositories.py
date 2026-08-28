from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.chunker import ChunkData
from app.notes.models import Note, NoteChunk


class NoteRepository:
    """Repository for Note persistence operations.

    All methods enforce tenant isolation via profile_id filtering.
    """

    @staticmethod
    async def create(
        session: AsyncSession,
        profile_id: UUID,
        title: str,
        content: str,
        folder_id: Optional[UUID] = None,
    ) -> Note:
        """Create and persist a new Note for the given profile_id."""
        note = Note(profile_id=profile_id, title=title, content=content, folder_id=folder_id)
        session.add(note)
        await session.commit()
        await session.refresh(note)
        return note

    @staticmethod
    async def list_by_profile(
        session: AsyncSession,
        profile_id: UUID,
        folder_id: Optional[UUID] = None,
    ) -> List[Note]:
        """Retrieve notes for a user, optionally scoped to a folder, newest first."""
        stmt = select(Note).where(Note.profile_id == profile_id)
        if folder_id is not None:
            stmt = stmt.where(Note.folder_id == folder_id)
        stmt = stmt.order_by(Note.created_at.desc())
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(session: AsyncSession, note_id: UUID) -> Optional[Note]:
        """Retrieve a single Note by id, unscoped by profile_id.

        Ownership must be checked by the caller (see NoteService.delete_note),
        matching the existing pattern already used there.
        """
        stmt = select(Note).where(Note.id == note_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def delete(session: AsyncSession, note: Note) -> None:
        """Delete a Note."""
        await session.delete(note)
        await session.commit()
        

class NoteChunkRepository:
    """Repository for NoteChunk persistence and lifecycle management.

    Handles bulk creation with chunk linking, tenant-isolated retrieval,
    embedding status updates, and deletions.
    """

    @staticmethod
    async def bulk_create_chunks(
        session: AsyncSession,
        chunks_data: List[ChunkData],
        note_id: UUID,
        profile_id: UUID,
        version: int = 1,
    ) -> List[NoteChunk]:
        """Persist multiple chunks for a note with automatic linking."""
        if not chunks_data:
            return []

        chunk_records: List[NoteChunk] = []
        
        # Step 1: Create NoteChunk records
        for chunk_data in chunks_data:
            chunk_record = NoteChunk(
                note_id=note_id,
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

        # Flush to generate IDs
        await session.flush()

        # Step 2: Link chunks in sequence
        for i in range(len(chunk_records)):
            if i > 0:
                chunk_records[i].previous_chunk_id = chunk_records[i - 1].id
            if i < len(chunk_records) - 1:
                chunk_records[i].next_chunk_id = chunk_records[i + 1].id

        await session.flush()
        return chunk_records
    
    @staticmethod
    async def get_chunks_by_note(
        session: AsyncSession,
        note_id: UUID,
        profile_id: UUID,
        version: Optional[int] = None,
    ) -> List[NoteChunk]:
        """Fetch all chunks for a note with strict multi-tenant isolation."""
        query = select(NoteChunk).where(
            and_(
                NoteChunk.note_id == note_id,
                NoteChunk.profile_id == profile_id,
            )
        )

        if version is not None:
            query = query.where(NoteChunk.version == version)

        query = query.order_by(NoteChunk.chunk_index)
        result = await session.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def update_embedding_status(
        session: AsyncSession,
        chunk_ids: List[UUID],
        status: str,
    ) -> None:
        """Update embedding_status for specified chunk IDs."""
        allowed_statuses = {"pending", "processing", "ready", "failed"}
        if status not in allowed_statuses:
            raise ValueError(
                f"Invalid embedding status: {status}. Must be one of: {', '.join(allowed_statuses)}"
            )

        if not chunk_ids:
            return

        stmt = (
            update(NoteChunk)
            .where(NoteChunk.id.in_(chunk_ids))
            .values(embedding_status=status)
        )
        await session.execute(stmt)
        await session.flush()
        
    
    @staticmethod
    async def delete_chunks_by_note(
        session: AsyncSession,
        note_id: UUID,
        profile_id: UUID,
    ) -> None:
        """Delete all chunks associated with a note for a given profile."""
        stmt = delete(NoteChunk).where(
            and_(
                NoteChunk.note_id == note_id,
                NoteChunk.profile_id == profile_id,
            )
        )
        await session.execute(stmt)
        await session.flush()



__all__ = ["NoteRepository", "NoteChunkRepository"]