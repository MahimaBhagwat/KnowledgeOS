from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.notes.schemas import NoteCreate, NoteOut
from app.notes.services import NoteService

router: APIRouter = APIRouter(prefix="/notes", tags=["notes"])
service = NoteService()


@router.post("/", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
async def create_note(
    payload: NoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> NoteOut:
    profile_id = UUID(current_user["profile_id"])
    note = await service.create_note(
        session=db,
        profile_id=profile_id,
        title=payload.title,
        content=payload.content,
        folder_id=payload.folder_id,
    )
    return NoteOut.model_validate(note)


@router.get("/", response_model=List[NoteOut])
async def list_notes(
    folder_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> List[NoteOut]:
    profile_id = UUID(current_user["profile_id"])
    notes = await service.get_notes(session=db, profile_id=profile_id, folder_id=folder_id)
    return [NoteOut.model_validate(note) for note in notes]


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> Response:
    profile_id = UUID(current_user["profile_id"])
    await service.delete_note(session=db, profile_id=profile_id, note_id=note_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["router"]
