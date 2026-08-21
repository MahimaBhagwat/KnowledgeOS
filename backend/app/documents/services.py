from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.documents import schemas
from app.documents.models import Document
from app.documents.repositories import DocumentRepository
from app.folders.repositories import FolderRepository


class DocumentService:
    """Orchestrates document business logic and enforces folder boundaries.

    Service methods ensure tenant isolation by always verifying that folders
    and documents belong to the provided profile_id before performing changes.
    """

    @staticmethod
    async def create_document(session: AsyncSession, doc_data: schemas.DocumentCreate, profile_id: UUID) -> Document:
        """Create a document ensuring the target folder belongs to the profile.

        If folder_id is missing or invalid, assign to the user's 'uploaded'
        system folder when available.
        """
        folder_id = doc_data.folder_id
        target_folder_id: Optional[UUID] = None

        if folder_id is not None:
            folder = await FolderRepository.get_by_id(session, folder_id, profile_id)
            if folder is None:
                # Treat invalid folder as not found
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target folder not found")
            target_folder_id = folder_id
        else:
            # Find user's uploaded system folder
            uploaded_folder = await FolderRepository.get_system_folder_by_type(session, profile_id, "uploaded")
            if uploaded_folder is None:
                # Auto-provision system folders if missing on the fly
                system_folders = await FolderService.create_default_system_folders(session, profile_id)
                uploaded_folder = system_folders[0]
            target_folder_id = uploaded_folder.id

        # Build a new DocumentCreate-like object with resolved folder_id
        create_data = doc_data.model_copy()
        create_data.folder_id = target_folder_id

        # Wrap repository call to intercept duplicate file name integrity errors
        try:
            document = await DocumentRepository.create(session, create_data, profile_id)
            return document
        except IntegrityError:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A document named '{doc_data.name}' already exists in this folder.",
            )

    @staticmethod
    async def get_document(session: AsyncSession, doc_id: UUID, profile_id: UUID, include_deleted: bool = False) -> Document:
        doc = await DocumentRepository.get_by_id(session, doc_id, profile_id, include_deleted=include_deleted)
        if doc is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        return doc

    @staticmethod
    async def list_user_documents(
        session: AsyncSession,
        profile_id: UUID,
        folder_id: Optional[UUID] = None,
        is_favorite: Optional[bool] = None,
        is_deleted: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Document]:
        return await DocumentRepository.get_user_documents(
            session, profile_id, folder_id=folder_id, is_favorite=is_favorite, is_deleted=is_deleted, skip=skip, limit=limit
        )

    @staticmethod
    async def update_document(session: AsyncSession, doc_id: UUID, update_data: schemas.DocumentUpdate, profile_id: UUID) -> Document:
        doc = await DocumentRepository.get_by_id(session, doc_id, profile_id, include_deleted=True)
        if doc is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

        # If moving folder, verify destination ownership
        updates = update_data.model_dump(exclude_none=True)
        new_folder_id = updates.get("folder_id")
        if new_folder_id is not None:
            dest_folder = await FolderRepository.get_by_id(session, new_folder_id, profile_id)
            if dest_folder is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Destination folder not found")

        updated = await DocumentRepository.update(session, doc, update_data)
        return updated

    @staticmethod
    async def soft_delete_document(session: AsyncSession, doc_id: UUID, profile_id: UUID) -> Document:
        doc = await DocumentRepository.get_by_id(session, doc_id, profile_id, include_deleted=False)
        if doc is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        return await DocumentRepository.soft_delete(session, doc)

    @staticmethod
    async def restore_document(session: AsyncSession, doc_id: UUID, profile_id: UUID) -> Document:
        doc = await DocumentRepository.get_by_id(session, doc_id, profile_id, include_deleted=True)
        if doc is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        if not doc.is_deleted:
            return doc
        return await DocumentRepository.restore(session, doc)

    @staticmethod
    async def permanently_delete_document(session: AsyncSession, doc_id: UUID, profile_id: UUID) -> None:
        doc = await DocumentRepository.get_by_id(session, doc_id, profile_id, include_deleted=True)
        if doc is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        await DocumentRepository.delete_permanently(session, doc)

    @staticmethod
    async def reassign_documents_from_folder(session: AsyncSession, folder_id: UUID, profile_id: UUID) -> int:
        """Reassign all active documents from folder_id to the user's 'uploaded' folder.

        Returns the number of documents reassigned.
        """
        # Verify source folder belongs to user
        source = await FolderRepository.get_by_id(session, folder_id, profile_id)
        if source is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source folder not found")

        uploaded = await FolderRepository.get_system_folder_by_type(session, profile_id, "uploaded")
        if uploaded is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User uploaded folder not found; cannot reassign documents",
            )

        docs = await DocumentRepository.get_user_documents(session, profile_id, folder_id=folder_id, is_deleted=False, skip=0, limit=10000)
        count = 0
        for doc in docs:
            # Move document to uploaded folder
            doc.folder_id = uploaded.id
            await DocumentRepository.update(session, doc, schemas.DocumentUpdate(folder_id=uploaded.id))
            count += 1
        return count


__all__ = ["DocumentService"]
