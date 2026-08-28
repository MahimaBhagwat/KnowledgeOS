from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.folders.models import Folder
from app.folders import schemas

from app.documents.models import Document

from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status


class FolderRepository:
    """Repository for Folder persistence operations.

    All methods are async and expect an external AsyncSession to be provided by
    the caller (dependency injection). Queries always enforce tenant scoping
    by filtering on profile_id to avoid cross-tenant data access.
    """

    @staticmethod
    async def create(
        session: AsyncSession,
        *,
        folder_data: schemas.FolderCreate,
        profile_id: UUID,
        folder_type: Optional[schemas.FolderType] = None,
        is_system_folder: bool = False,
        commit: bool = True,
    ) -> Folder:
        """Persist a new Folder bound to the provided profile_id.

        The folder_data is a validated Pydantic schema. If the underlying ORM
        model supports an explicit `folder_type` column it will be set; if not,
        the value is stored in the `name` and `is_system_folder` columns only.
        """
        data = folder_data.model_dump()
        # Build ORM kwargs explicitly to avoid unexpected keys
        orm_kwargs = {
            "profile_id": profile_id,
            "name": data.get("name"),
            "is_system_folder": is_system_folder,
        }
        # Only include folder_type if the model exposes that attribute
        if hasattr(Folder, "folder_type") and folder_type is not None:
            orm_kwargs["folder_type"] = folder_type

        folder = Folder(**orm_kwargs)
        session.add(folder)
        if commit:
            await session.commit()
            await session.refresh(folder)
        return folder

    @staticmethod
    async def get_by_id(session: AsyncSession, folder_id: UUID, profile_id: UUID) -> Optional[Folder]:
        """Retrieve a folder by id while enforcing tenant isolation by profile_id."""
        stmt = (
            select(Folder, func.count(Document.id).label("document_count"))
            .outerjoin(Document, Document.folder_id == Folder.id)
            .where(Folder.id == folder_id, Folder.profile_id == profile_id)
            .group_by(Folder.id)
        )
        result = await session.execute(stmt)
        row = result.first()
        if row is None:
            return None
        
        folder, count = row
        folder.document_count = count
        return folder

    @staticmethod
    async def get_user_folders(session: AsyncSession, profile_id: UUID) -> List[Folder]:
        """Return all folders that belong to the given profile_id."""
        stmt = (
            select(Folder, func.count(Document.id).label("document_count"))
            .outerjoin(Document, Document.folder_id == Folder.id)
            .where(Folder.profile_id == profile_id)
            .group_by(Folder.id)
            .order_by(Folder.name)
        )
        result = await session.execute(stmt)

        folders: List[Folder] = []
        for folder, count in result.tuples():
            # Dynamically attach document_count to the ORM instance
            folder.document_count = count
            folders.append(folder)
            
        return folders

    @staticmethod
    async def get_system_folder_by_type(
        session: AsyncSession, profile_id: UUID, folder_type: schemas.FolderType
    ) -> Optional[Folder]:
        """Locate a user's system-managed folder by its logical folder_type.

        This method prefers an explicit `folder_type` column when present on the
        ORM model; as a fallback it searches for a system folder by matching the
        `is_system_folder` flag and a normalized name equal to the folder_type
        string. This approach keeps the repository robust across small schema
        evolution differences.
        """
        if hasattr(Folder, "folder_type"):
            stmt = select(Folder).where(
                Folder.profile_id == profile_id, Folder.folder_type == folder_type, Folder.is_system_folder == True
            )
        else:
            # Fallback: match by is_system_folder and name equality
            stmt = select(Folder).where(
                Folder.profile_id == profile_id, Folder.is_system_folder == True, Folder.name == folder_type
            )
        result = await session.execute(stmt)
        return result.scalars().first()

    # @staticmethod
    # async def update(
    #     session: AsyncSession, folder_entity: Folder, *, update_data: schemas.FolderUpdate, commit: bool = True
    # ) -> Folder:
    #     """Apply partial updates from the provided FolderUpdate schema to the
    #     folder_entity and persist changes.
    #     """
    #     updates = update_data.model_dump(exclude_none=True)
    #     for key, value in updates.items():
    #         if hasattr(folder_entity, key):
    #             setattr(folder_entity, key, value)
    #     session.add(folder_entity)
    #     if commit:
    #         await session.commit()
    #         await session.refresh(folder_entity)
    #     return folder_entity


    @staticmethod
    async def update(session, folder_entity, update_data, commit=True):
        for key, value in update_data.model_dump(exclude_unset=True).items():
            setattr(folder_entity, key, value)
        session.add(folder_entity)
        if commit:
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A folder with this name already exists.",
                )
            await session.refresh(folder_entity)
        return folder_entity


    @staticmethod
    async def delete(session: AsyncSession, folder_entity: Folder, *, commit: bool = True) -> None:
        """Delete the provided folder entity. Caller must ensure the folder is
        allowed to be deleted (e.g., system folders may be protected by higher
        level business logic).
        """
        await session.delete(folder_entity)
        if commit:
            await session.commit()


__all__ = ["FolderRepository"]
