from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.folders.repositories import FolderRepository

# NoteRepository is expected to be implemented elsewhere according to the project architecture.
# The service delegates persistence concerns to the repository to keep business logic thin.
try:
    from app.notes.repositories import NoteRepository  # type: ignore
except Exception:  # pragma: no cover - repository may not exist during incremental implementation
    NoteRepository = None  # type: ignore


class NoteService:
    """Service layer for quick note management.

    This service delegates database operations to a NoteRepository implementation
    (not included here). Methods raise HTTPException when operations fail due to
    missing resources or unauthorized access.
    """

    @staticmethod
    @staticmethod
    async def create_note(
        session: AsyncSession,
        profile_id: UUID,
        title: str,
        content: str,
        folder_id: Optional[UUID] = None,
    ) -> Any:
        """Create a quick note owned by profile_id.

        If folder_id is not provided, defaults to the user's "Quick Notes" system
        folder, mirroring the same fallback pattern used for document uploads.

        The implementation delegates to NoteRepository.create. If the repository
        is not available, raise an informative RuntimeError to indicate missing
        infrastructure during incremental implementation.
        """
        if NoteRepository is None:
            raise RuntimeError("NoteRepository is not available in this build. Implement app.notes.repositories.NoteRepository before using NoteService.")

        # Preserve folder_id as provided (including None). Do not attempt to
        # force-resolve a non-existent "quick_notes" system folder for new users.
        note = await NoteRepository.create(session=session, profile_id=profile_id, title=title, content=content, folder_id=folder_id)
        return note

    @staticmethod
    async def get_notes(session: AsyncSession, profile_id: UUID, folder_id: Optional[UUID] = None) -> List[Any]:
        """Retrieve notes for a user, optionally scoped to a folder."""
        if NoteRepository is None:
            raise RuntimeError("NoteRepository is not available in this build. Implement app.notes.repositories.NoteRepository before using NoteService.")

        notes = await NoteRepository.list_by_profile(session=session, profile_id=profile_id, folder_id=folder_id)
        return notes

    @staticmethod
    async def delete_note(session: AsyncSession, profile_id: UUID, note_id: UUID) -> None:
        """Delete a note owned by profile_id.

        Raises HTTPException(404) if the note does not exist or does not belong to
        the provided profile_id.
        """
        if NoteRepository is None:
            raise RuntimeError("NoteRepository is not available in this build. Implement app.notes.repositories.NoteRepository before using NoteService.")

        note = await NoteRepository.get_by_id(session=session, note_id=note_id)
        if note is None or getattr(note, "profile_id", None) != profile_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

        await NoteRepository.delete(session=session, note=note)


__all__ = ["NoteService"]
