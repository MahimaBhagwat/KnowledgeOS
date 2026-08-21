from __future__ import annotations

from typing import List, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.folders import schemas
from app.folders.repositories import FolderRepository
from app.folders.services import FolderService
from app.core.logging import get_logger

logger = get_logger(__name__)

router: APIRouter = APIRouter(prefix="/folders", tags=["folders"])


@router.post("/", response_model=schemas.FolderOut, status_code=status.HTTP_201_CREATED)
async def create_folder(
    payload: schemas.FolderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, str] = Depends(get_current_user),
) -> schemas.FolderOut:
    profile_id = UUID(current_user.get("profile_id"))
    folder = await FolderService.create_custom_folder(db, payload, profile_id)
    return schemas.FolderOut.model_validate(folder)


@router.get("/", response_model=List[schemas.FolderOut])
async def list_folders(
    db: AsyncSession = Depends(get_db), current_user: Dict[str, str] = Depends(get_current_user)
) -> List[schemas.FolderOut]:
    profile_id = UUID(current_user.get("profile_id"))
    folders = await FolderRepository.get_user_folders(db, profile_id)
    return [schemas.FolderOut.model_validate(f) for f in folders]


@router.patch("/{folder_id}", response_model=schemas.FolderOut)
async def patch_folder(
    folder_id: UUID,
    payload: schemas.FolderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, str] = Depends(get_current_user),
) -> schemas.FolderOut:
    profile_id = UUID(current_user.get("profile_id"))
    folder = await FolderRepository.get_by_id(db, folder_id, profile_id)
    if folder is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")

    try:
        updated = await FolderService.update_folder(db, folder, payload)
    except HTTPException:
        raise
    return schemas.FolderOut.model_validate(updated)


@router.delete("/{folder_id}", response_class=Response, status_code=status.HTTP_204_NO_CONTENT)
async def delete_folder(
    folder_id: UUID, db: AsyncSession = Depends(get_db), current_user: Dict[str, str] = Depends(get_current_user)
) -> Response:
    profile_id = UUID(current_user.get("profile_id"))
    folder = await FolderRepository.get_by_id(db, folder_id, profile_id)
    if folder is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")

    await FolderService.delete_folder(db, folder)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
