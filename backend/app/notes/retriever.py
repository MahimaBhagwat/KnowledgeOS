from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.vector_store import VectorStoreManager
from app.notes.models import NoteChunk
from app.notes.repositories import NoteChunkRepository, NoteRepository


class NoteRetrieverContext(BaseModel):
    """Structured retrieval result for a user note chunk."""

    chunk_id: UUID
    note_id: UUID
    chunk_index: int
    chunk_text: str
    similarity_score: float
    version: int
    metadata: Dict[str, Any]
    note_title: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class NoteRetriever:
    """
    Retrieve relevant note chunks from ChromaDB and PostgreSQL.

    Performs vector similarity search on note chunks, validates note ownership
    in PostgreSQL, and expands the context with neighboring chunks when applicable.
    """

    def __init__(self, vector_store_manager: Optional[VectorStoreManager] = None) -> None:
        self._vector_store_manager = vector_store_manager

    def _get_vector_store(self) -> VectorStoreManager:
        """Return a cached vector store manager instance."""
        if self._vector_store_manager is None:
            self._vector_store_manager = VectorStoreManager()
        return self._vector_store_manager

    @staticmethod
    def _score_from_distance(distance: Optional[float]) -> float:
        """Convert Chroma distance into a descending similarity score."""
        if distance is None:
            return 0.0
        return max(0.0, 1.0 - float(distance))

    @staticmethod
    def _build_context(
        chunk: NoteChunk,
        similarity_score: float,
        metadata: Dict[str, Any],
        note_title: Optional[str] = None,
    ) -> NoteRetrieverContext:
        """Convert an ORM NoteChunk row into a NoteRetrieverContext payload."""
        return NoteRetrieverContext(
            chunk_id=chunk.id,
            note_id=chunk.note_id,
            chunk_index=chunk.chunk_index,
            chunk_text=chunk.chunk_text,
            similarity_score=similarity_score,
            version=chunk.version,
            metadata=metadata,
            note_title=note_title,
        )

    @staticmethod
    def _chunk_metadata(
        chunk: NoteChunk,
        folder_id: Optional[UUID],
        is_neighbor: bool = False,
        note_title: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build a metadata dictionary for a retrieved note context chunk."""
        metadata: Dict[str, Any] = {
            "chunk_id": str(chunk.id),
            "note_id": str(chunk.note_id),
            "profile_id": str(chunk.profile_id),
            "source_type": "note",
            "chunk_index": int(chunk.chunk_index),
            "version": int(chunk.version),
            "token_count": int(chunk.token_count),
            "overlap_tokens": int(chunk.overlap_tokens),
            "embedding_status": str(getattr(chunk, "embedding_status", "pending")),
        }
        if folder_id is not None:
            metadata["folder_id"] = str(folder_id)
        if note_title:
            metadata["title"] = str(note_title)
        if is_neighbor:
            metadata["is_neighbor"] = True
        return metadata

    @staticmethod
    def _select_chunk_map(chunks: List[NoteChunk]) -> Dict[UUID, NoteChunk]:
        return {chunk.id: chunk for chunk in chunks}

    async def retrieve_relevant_chunks(
        self,
        session: AsyncSession,
        query_embedding: List[float],
        profile_id: UUID,
        folder_id: Optional[UUID] = None,
        top_k: int = 5,
        score_threshold: float = 0.0,
    ) -> List[NoteRetrieverContext]:
        """
        Retrieve semantically relevant note chunks with tenant isolation.
        Queries ChromaDB for note chunks, validates ownership in PostgreSQL,
        and expands context with adjacent chunks.
        """
        if not query_embedding:
            return []

        vector_results = self._get_vector_store().similarity_search_notes(
            query_embedding=query_embedding,
            profile_id=profile_id,
            top_k=top_k,
            folder_id=folder_id,
        )

        filtered_results: List[Dict[str, Any]] = []
        for result in vector_results:
            score = self._score_from_distance(result.get("distance"))
            if score >= score_threshold:
                item = dict(result)
                item["similarity_score"] = score
                filtered_results.append(item)

        grouped_by_note: Dict[UUID, List[Dict[str, Any]]] = {}
        for result in filtered_results:
            metadata = result.get("metadata", {})
            note_id_raw = metadata.get("note_id")
            if not note_id_raw:
                continue
            try:
                note_uuid = UUID(str(note_id_raw))
            except (TypeError, ValueError):
                continue
            grouped_by_note.setdefault(note_uuid, []).append(result)

        contexts_by_chunk_id: Dict[UUID, NoteRetrieverContext] = {}

        for note_id, note_hits in grouped_by_note.items():
            note = await NoteRepository.get_by_id(session, note_id)
            if note is None or getattr(note, "profile_id", None) != profile_id:
                continue

            chunks = await NoteChunkRepository.get_chunks_by_note(
                session,
                note_id=note_id,
                profile_id=profile_id,
            )
            if not chunks:
                continue

            chunk_map = self._select_chunk_map(chunks)
            sorted_hits = sorted(
                note_hits,
                key=lambda item: float(item.get("similarity_score", 0.0)),
                reverse=True,
            )

            for hit in sorted_hits:
                metadata = hit.get("metadata", {})
                chunk_id_raw = metadata.get("chunk_id") or hit.get("id")
                if not chunk_id_raw:
                    continue

                try:
                    chunk_id = UUID(str(chunk_id_raw))
                except ValueError:
                    continue

                anchor_chunk = chunk_map.get(chunk_id)
                if anchor_chunk is None:
                    continue

                anchor_score = float(hit.get("similarity_score", 0.0))
                folder_value: Optional[UUID] = getattr(note, "folder_id", None)
                if folder_value is None and metadata.get("folder_id"):
                    try:
                        folder_value = UUID(str(metadata["folder_id"]))
                    except ValueError:
                        folder_value = None

                contexts_by_chunk_id[anchor_chunk.id] = self._build_context(
                    anchor_chunk,
                    anchor_score,
                    self._chunk_metadata(anchor_chunk, folder_value, note_title=note.title),
                    note_title=note.title,
                )

                neighbor_indices = (anchor_chunk.chunk_index - 1, anchor_chunk.chunk_index + 1)
                for offset_index in neighbor_indices:
                    neighbor = next(
                        (c for c in chunks if c.chunk_index == offset_index),
                        None,
                    )
                    if neighbor is None or neighbor.id in contexts_by_chunk_id:
                        continue

                    neighbor_score = max(0.0, anchor_score - 0.001)
                    contexts_by_chunk_id[neighbor.id] = self._build_context(
                        neighbor,
                        neighbor_score,
                        self._chunk_metadata(neighbor, folder_value, is_neighbor=True, note_title=note.title),
                        note_title=note.title,
                    )

        contexts = sorted(
            contexts_by_chunk_id.values(),
            key=lambda context: (context.similarity_score, -context.chunk_index),
            reverse=True,
        )
        return contexts

    def format_context_for_llm(self, contexts: List[NoteRetrieverContext]) -> str:
        """
        Format retrieved note contexts into a prompt-ready block.
        """
        if not contexts:
            return ""

        lines: List[str] = []
        current_note_id: Optional[UUID] = None

        for context in contexts:
            if current_note_id != context.note_id:
                current_note_id = context.note_id
                title_str = f" - \"{context.note_title}\"" if context.note_title else ""
                lines.append(f"[Note {current_note_id}{title_str}]")

            lines.append(
                f"[Chunk {context.chunk_index} | Score {context.similarity_score:.4f} | Version {context.version}]"
            )
            lines.append(context.chunk_text.strip())
            lines.append("")

        return "\n".join(lines).strip()


__all__ = ["NoteRetrieverContext", "NoteRetriever"]
