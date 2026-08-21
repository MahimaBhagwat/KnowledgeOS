from __future__ import annotations

from typing import List, Optional, Sequence
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.embeddings import generate_embeddings
from app.documents.repositories import DocumentRepository
from app.ingestion.chunker import TextChunker
from app.ingestion.models import DocumentChunk
from app.ingestion.parsers import DocumentParserFactory, FileParsingError
from app.ingestion.repositories import DocumentChunkRepository
from app.ingestion.vector_store import VectorStoreManager


class IngestionService:
    """Orchestrates the document ingestion pipeline.

    The service coordinates parsing, semantic chunking, persistence, embedding
    generation, and ChromaDB indexing while preserving tenant isolation.
    """

    def __init__(
        self,
        vector_store_manager: Optional[VectorStoreManager] = None,
    ) -> None:
        self._vector_store_manager = vector_store_manager

    def _get_vector_store(self) -> VectorStoreManager:
        """Return a configured vector store manager, instantiating lazily."""
        if self._vector_store_manager is None:
            self._vector_store_manager = VectorStoreManager()
        return self._vector_store_manager

    @staticmethod
    def _prepare_chunk_metadata(
        chunks: Sequence[DocumentChunk],
        folder_id: Optional[UUID],
    ) -> None:
        """Attach transient folder metadata for vector indexing."""
        if folder_id is None:
            return
        for chunk in chunks:
            setattr(chunk, "folder_id", folder_id)

    async def _mark_chunks_status(
        self,
        session: AsyncSession,
        chunk_ids: Sequence[UUID],
        status_name: str,
    ) -> None:
        """Update chunk lifecycle state and persist it immediately."""
        await DocumentChunkRepository.update_embedding_status(
            session,
            list(chunk_ids),
            status_name,
        )
        await session.commit()

    async def process_document(
        self,
        session: AsyncSession,
        document_id: UUID,
        profile_id: UUID,
        file_bytes: bytes,
        file_type: str,
        folder_id: Optional[UUID] = None,
    ) -> List[DocumentChunk]:
        """Parse, chunk, embed, and index a document.

        The workflow persists chunks to PostgreSQL, indexes them into ChromaDB,
        and synchronizes chunk embedding status throughout the process.
        """
        document = await DocumentRepository.get_by_id(
            session,
            document_id,
            profile_id,
            include_deleted=False,
        )
        if document is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

        resolved_folder_id = folder_id if folder_id is not None else document.folder_id
        chunk_ids: List[UUID] = []
        created_chunks: List[DocumentChunk] = []

        try:
            parser = DocumentParserFactory.get_parser(file_type)
            parsed_text = parser.parse(file_bytes)
            if not parsed_text.strip():
                raise RuntimeError("Document parsing produced no text content.")

            chunker = TextChunker()
            chunk_data = chunker.create_chunks(parsed_text)
            if not chunk_data:
                raise RuntimeError("Document chunking produced no chunks.")

            created_chunks = await DocumentChunkRepository.bulk_create_chunks(
                session=session,
                chunks_data=chunk_data,
                document_id=document_id,
                profile_id=profile_id,
                version=int(document.version or 1),
            )
            chunk_ids = [chunk.id for chunk in created_chunks]

            for chunk in created_chunks:
                chunk.embedding_status = "processing"

            await self._mark_chunks_status(session, chunk_ids, "processing")

            embeddings = generate_embeddings([chunk.chunk_text for chunk in created_chunks])
            self._prepare_chunk_metadata(created_chunks, resolved_folder_id)

            for chunk in created_chunks:
                chunk.embedding_status = "ready"

            self._get_vector_store().add_document_chunks(
                document_id=document_id,
                profile_id=profile_id,
                chunks=created_chunks,
                embeddings=embeddings,
            )

            await self._mark_chunks_status(session, chunk_ids, "ready")

            return created_chunks
        except HTTPException:
            raise
        except FileParsingError as exc:
            if chunk_ids:
                try:
                    await DocumentChunkRepository.update_embedding_status(
                        session,
                        chunk_ids,
                        "failed",
                    )
                    await session.commit()
                except Exception:
                    await session.rollback()
            raise RuntimeError(
                f"Failed to parse document {document_id}: {exc}"
            ) from exc
        except Exception as exc:
            if chunk_ids:
                try:
                    await DocumentChunkRepository.update_embedding_status(
                        session,
                        chunk_ids,
                        "failed",
                    )
                    await session.commit()
                except Exception:
                    await session.rollback()

                try:
                    self._get_vector_store().delete_document_vectors(document_id)
                except Exception:
                    pass

            raise RuntimeError(
                f"Failed to process document {document_id}: {exc}"
            ) from exc


__all__ = ["IngestionService"]
