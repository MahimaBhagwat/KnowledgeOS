from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.documents.models import Document
from app.documents import schemas


class DocumentRepository:
    """Repository for Document persistence operations.

    All public methods require an AsyncSession provided by the caller. Every
    query strictly filters by profile_id to enforce multi-tenant isolation.
    """

    @staticmethod
    async def create(session: AsyncSession, doc_data: schemas.DocumentCreate, profile_id: UUID) -> Document:
        """Create and persist a new Document bound to the provided profile_id."""
        data = doc_data.model_dump()
        orm_kwargs = {
            "profile_id": profile_id,
            "folder_id": data.get("folder_id"),
            "name": data.get("name"),
            "file_path": data.get("file_path"),
            "file_type": data.get("file_type").value if isinstance(data.get("file_type"), schemas.DocumentTypeEnum) else data.get("file_type"),
            "file_size": data.get("file_size"),
        }
        document = Document(**orm_kwargs)
        session.add(document)
        await session.commit()
        await session.refresh(document)
        return document

    @staticmethod
    async def get_by_id(
        session: AsyncSession, doc_id: UUID, profile_id: UUID, include_deleted: bool = False
    ) -> Optional[Document]:
        """Retrieve a document by id while enforcing tenant isolation.

        By default soft-deleted documents are excluded unless include_deleted=True.
        """
        stmt = select(Document).where(Document.id == doc_id, Document.profile_id == profile_id)
        if not include_deleted:
            stmt = stmt.where(Document.is_deleted == False)
        result = await session.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def get_user_documents(
        session: AsyncSession,
        profile_id: UUID,
        folder_id: Optional[UUID] = None,
        is_favorite: Optional[bool] = None,
        is_deleted: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Document]:
        """Fetch user documents with optional filtering and pagination.

        Results are ordered by created_at descending to surface recent uploads.
        """
        stmt = select(Document).where(Document.profile_id == profile_id, Document.is_deleted == is_deleted)

        if folder_id is not None:
            stmt = stmt.where(Document.folder_id == folder_id)
        if is_favorite is not None:
            stmt = stmt.where(Document.is_favorite == is_favorite)

        stmt = stmt.order_by(Document.created_at.desc()).offset(skip).limit(limit)
        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def update(session: AsyncSession, doc_entity: Document, update_data: schemas.DocumentUpdate) -> Document:
        """Apply partial updates to the document entity and persist changes."""
        updates = update_data.model_dump(exclude_none=True)
        for key, value in updates.items():
            if hasattr(doc_entity, key):
                setattr(doc_entity, key, value)
        # increment version on changes (optional behavior)
        if updates:
            try:
                doc_entity.version = (doc_entity.version or 1) + 1
            except Exception:
                doc_entity.version = 1
        session.add(doc_entity)
        await session.commit()
        await session.refresh(doc_entity)
        return doc_entity

    @staticmethod
    async def soft_delete(session: AsyncSession, doc_entity: Document) -> Document:
        """Soft-delete a document by setting is_deleted=True."""
        doc_entity.is_deleted = True
        # advance version for audit
        try:
            doc_entity.version = (doc_entity.version or 1) + 1
        except Exception:
            doc_entity.version = 1
        session.add(doc_entity)
        await session.commit()
        await session.refresh(doc_entity)
        return doc_entity

    @staticmethod
    async def restore(session: AsyncSession, doc_entity: Document) -> Document:
        """Restore a soft-deleted document by setting is_deleted=False."""
        doc_entity.is_deleted = False
        try:
            doc_entity.version = (doc_entity.version or 1) + 1
        except Exception:
            doc_entity.version = 1
        session.add(doc_entity)
        await session.commit()
        await session.refresh(doc_entity)
        return doc_entity

    @staticmethod
    async def delete_permanently(session: AsyncSession, doc_entity: Document) -> None:
        """Permanently remove the document record from the database."""
        await session.delete(doc_entity)
        await session.commit()


__all__ = ["DocumentRepository"]
