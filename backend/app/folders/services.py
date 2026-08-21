from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.folders import schemas
from app.folders.models import Folder
from app.folders.repositories import FolderRepository


class FolderService:
    """Orchestrates folder business logic and enforces lifecycle rules.

    The service layer performs multi-step operations atomically and enforces
    business constraints such as protecting system folders from mutation.
    """

    SYSTEM_FOLDERS = [
        ("uploaded", "Uploaded"),
    ]

    @staticmethod
    async def create_default_system_folders(
        session: AsyncSession,
        profile_id: UUID,
        commit: bool = True,
    ) -> List[Folder]:
        """Atomically create required system folders for a new profile.

        Creates the three system folders using commit=False and performs a
        single commit at the end. Rolls back the transaction on any failure.
        Returns the list of created Folder instances in the same order as
        SYSTEM_FOLDERS.
        """
        created: List[Folder] = []
        try:
            for folder_type, display_name in FolderService.SYSTEM_FOLDERS:
                folder_data = schemas.FolderCreate(name=display_name)
                # Attempt to set folder_type where supported; repository will
                # handle absence of the column gracefully.
                folder = await FolderRepository.create(
                    session,
                    folder_data=folder_data,
                    profile_id=profile_id,
                    folder_type=folder_type,
                    is_system_folder=True,
                    commit=False,
                )
                created.append(folder)

            if commit:
                await session.commit()

                # Refresh instances to populate defaults
                for folder in created:
                    await session.refresh(folder)

            return created
        except Exception:
            await session.rollback()
            raise

    @staticmethod
    async def create_custom_folder(session: AsyncSession, folder_data: schemas.FolderCreate, profile_id: UUID) -> Folder:
        """Create a user-owned custom folder.

        Ensures is_system_folder is False and sets folder_type to 'custom'.
        """
        folder = await FolderRepository.create(
            session,
            folder_data=folder_data,
            profile_id=profile_id,
            folder_type="custom",
            is_system_folder=False,
            commit=True,
        )
        return folder

    @staticmethod
    async def update_folder(session: AsyncSession, folder_entity: Folder, update_data: schemas.FolderUpdate) -> Folder:
        """Update a folder's mutable fields. System folders are immutable.

        Raises HTTPException 400 if attempting to update a system folder.
        """
        if folder_entity.is_system_folder:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="System folders cannot be modified",
            )

        updated = await FolderRepository.update(session, folder_entity, update_data=update_data, commit=True)
        return updated

    @staticmethod
    async def delete_folder(session: AsyncSession, folder_entity: Folder) -> None:
        """Delete a custom folder. Prevent deletion of system folders.

        Raises HTTPException 400 when attempting to delete a system folder.
        """
        if folder_entity.is_system_folder:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="System folders cannot be deleted",
            )

        await FolderRepository.delete(session, folder_entity, commit=True)


__all__ = ["FolderService"]
