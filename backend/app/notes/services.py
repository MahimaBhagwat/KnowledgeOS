from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.embeddings import generate_embeddings
from app.ingestion.chunker import TextChunker
from app.ingestion.vector_store import VectorStoreManager
from app.notes.models import Note, NoteChunk
from app.notes.repositories import NoteChunkRepository, NoteRepository


class NoteIngestionService:
    """Orchestrates the user note ingestion pipeline for RAG.

    Coordinates semantic chunking, persistence, embedding generation,
    and ChromaDB vector indexing while preserving tenant isolation.
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

    async def process_note(
        self,
        session: AsyncSession,
        note: Note,
    ) -> List[NoteChunk]:
        """Chunk, embed, and index a user note into PostgreSQL and ChromaDB."""
        text_to_chunk = f"{note.title}\n\n{note.content}".strip() if note.title else note.content.strip()
        if not text_to_chunk:
            return []

        chunk_ids: List[UUID] = []
        created_chunks: List[NoteChunk] = []

        try:
            chunker = TextChunker()
            chunk_data = chunker.create_chunks(text_to_chunk)
            if not chunk_data:
                return []

            created_chunks = await NoteChunkRepository.bulk_create_chunks(
                session=session,
                chunks_data=chunk_data,
                note_id=note.id,
                profile_id=note.profile_id,
                version=1,
            )
            chunk_ids = [chunk.id for chunk in created_chunks]

            await NoteChunkRepository.update_embedding_status(session, chunk_ids, "processing")
            await session.commit()

            embeddings = generate_embeddings([chunk.chunk_text for chunk in created_chunks])

            self._get_vector_store().add_note_chunks(
                note_id=note.id,
                profile_id=note.profile_id,
                chunks=created_chunks,
                embeddings=embeddings,
                folder_id=note.folder_id,
                note_title=note.title,
            )

            await NoteChunkRepository.update_embedding_status(session, chunk_ids, "ready")
            await session.commit()

            return created_chunks
        except Exception as exc:
            if chunk_ids:
                try:
                    await NoteChunkRepository.update_embedding_status(
                        session,
                        chunk_ids,
                        "failed",
                    )
                    await session.commit()
                except Exception:
                    await session.rollback()

                try:
                    self._get_vector_store().delete_note_vectors(note.id)
                except Exception:
                    pass

            raise RuntimeError(
                f"Failed to process note {note.id}: {exc}"
            ) from exc

    async def delete_note_vectors_and_chunks(
        self,
        session: AsyncSession,
        note_id: UUID,
        profile_id: UUID,
    ) -> None:
        """Delete vector embeddings in ChromaDB and chunk records in PostgreSQL."""
        try:
            self._get_vector_store().delete_note_vectors(note_id)
        except Exception:
            pass

        await NoteChunkRepository.delete_chunks_by_note(
            session=session,
            note_id=note_id,
            profile_id=profile_id,
        )


class NoteService:
    """Service layer for quick note management.

    Delegates persistence to NoteRepository and vector search indexing to NoteIngestionService.
    """

    @staticmethod
    async def create_note(
        session: AsyncSession,
        profile_id: UUID,
        title: str,
        content: str,
        folder_id: Optional[UUID] = None,
        ingest_rag: bool = True,
    ) -> Note:
        """Create a quick note owned by profile_id and index it into RAG."""
        note = await NoteRepository.create(
            session=session,
            profile_id=profile_id,
            title=title,
            content=content,
            folder_id=folder_id,
        )

        if ingest_rag:
            ingestion_service = NoteIngestionService()
            await ingestion_service.process_note(session=session, note=note)

        return note

    @staticmethod
    async def get_notes(session: AsyncSession, profile_id: UUID, folder_id: Optional[UUID] = None) -> List[Note]:
        """Retrieve notes for a user, optionally scoped to a folder."""
        return await NoteRepository.list_by_profile(session=session, profile_id=profile_id, folder_id=folder_id)

    @staticmethod
    async def delete_note(session: AsyncSession, profile_id: UUID, note_id: UUID) -> None:
        """Delete a note owned by profile_id, including its vectors and chunks."""
        note = await NoteRepository.get_by_id(session=session, note_id=note_id)
        if note is None or getattr(note, "profile_id", None) != profile_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

        # Cleanup vector store and chunk records
        ingestion_service = NoteIngestionService()
        await ingestion_service.delete_note_vectors_and_chunks(
            session=session,
            note_id=note_id,
            profile_id=profile_id,
        )

        await NoteRepository.delete(session=session, note=note)


__all__ = ["NoteService", "NoteIngestionService"]

