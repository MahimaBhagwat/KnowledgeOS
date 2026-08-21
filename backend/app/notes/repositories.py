from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.notes.models import Note


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


__all__ = ["NoteRepository"]