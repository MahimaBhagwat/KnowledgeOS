from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.documents.repositories import DocumentRepository
from app.ingestion.models import DocumentChunk
from app.ingestion.repositories import DocumentChunkRepository
from app.ingestion.vector_store import VectorStoreManager


class RetrieverContext(BaseModel):
    """Structured retrieval result returned by the semantic retriever."""

    chunk_id: UUID
    document_id: UUID
    chunk_index: int
    chunk_text: str
    similarity_score: float
    version: int
    metadata: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class SemanticRetriever:
    """
    Retrieve relevant document chunks from ChromaDB and PostgreSQL.

    The retriever performs vector search first, then validates the owning
    document in PostgreSQL, and finally expands the result set with neighboring
    context chunks when appropriate.
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
        chunk: DocumentChunk,
        similarity_score: float,
        metadata: Dict[str, Any],
    ) -> RetrieverContext:
        """Convert an ORM chunk row into a RetrieverContext payload."""
        return RetrieverContext(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            chunk_index=chunk.chunk_index,
            chunk_text=chunk.chunk_text,
            similarity_score=similarity_score,
            version=chunk.version,
            metadata=metadata,
        )

    @staticmethod
    def _chunk_metadata(
        chunk: DocumentChunk,
        folder_id: Optional[UUID],
        is_neighbor: bool = False,
    ) -> Dict[str, Any]:
        """Build a metadata dictionary for a retrieval context chunk."""
        metadata: Dict[str, Any] = {
            "chunk_id": str(chunk.id),
            "document_id": str(chunk.document_id),
            "profile_id": str(chunk.profile_id),
            "chunk_index": int(chunk.chunk_index),
            "version": int(chunk.version),
            "token_count": int(chunk.token_count),
            "overlap_tokens": int(chunk.overlap_tokens),
            "embedding_status": str(getattr(chunk, "embedding_status", "pending")),
        }
        if folder_id is not None:
            metadata["folder_id"] = str(folder_id)
        if is_neighbor:
            metadata["is_neighbor"] = True
        return metadata

    @staticmethod
    def _select_chunk_map(
        chunks: List[DocumentChunk],
    ) -> Dict[UUID, DocumentChunk]:
        return {chunk.id: chunk for chunk in chunks}

    async def retrieve_relevant_chunks(
        self,
        session: AsyncSession,
        query_embedding: List[float],
        profile_id: UUID,
        folder_id: Optional[UUID] = None,
        top_k: int = 5,
        score_threshold: float = 0.0,
    ) -> List[RetrieverContext]:
        """
        Retrieve semantically relevant chunks with tenant isolation.

        The retriever first queries ChromaDB, then validates the owning
        document in PostgreSQL and expands the context with neighboring chunks
        when adjacent chunks exist in the same document.
        """
        vector_results = self._get_vector_store().similarity_search(
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

        grouped_by_document: Dict[Tuple[UUID, int], List[Dict[str, Any]]] = {}
        for result in filtered_results:
            metadata = result.get("metadata", {})
            document_id_raw = metadata.get("document_id")
            version_raw = metadata.get("version")
            if not document_id_raw:
                continue
            try:
                document_uuid = UUID(str(document_id_raw))
                version_value = int(version_raw)
            except (TypeError, ValueError):
                continue
            grouped_by_document.setdefault((document_uuid, version_value), []).append(result)

        contexts_by_chunk_id: Dict[UUID, RetrieverContext] = {}

        for (document_id, version_value), document_hits in grouped_by_document.items():
            document = await DocumentRepository.get_by_id(
                session,
                document_id,
                profile_id,
                include_deleted=False,
            )
            if document is None:
                continue
            if int(document.version or 1) != version_value:
                continue

            chunks = await DocumentChunkRepository.get_chunks_by_document(
                session,
                document_id=document_id,
                profile_id=profile_id,
                version=version_value,
            )
            if not chunks:
                continue

            chunk_map = self._select_chunk_map(chunks)
            sorted_hits = sorted(
                document_hits,
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
                folder_value: Optional[UUID] = None
                folder_id_raw = metadata.get("folder_id")
                if folder_id_raw:
                    try:
                        folder_value = UUID(str(folder_id_raw))
                    except ValueError:
                        folder_value = None

                contexts_by_chunk_id[anchor_chunk.id] = self._build_context(
                    anchor_chunk,
                    anchor_score,
                    self._chunk_metadata(anchor_chunk, folder_value),
                )

                neighbor_indices = (anchor_chunk.chunk_index - 1, anchor_chunk.chunk_index + 1)
                for offset_index in neighbor_indices:
                    neighbor = next(
                        (chunk for chunk in chunks if chunk.chunk_index == offset_index),
                        None,
                    )
                    if neighbor is None or neighbor.id in contexts_by_chunk_id:
                        continue

                    neighbor_score = max(0.0, anchor_score - 0.001)
                    contexts_by_chunk_id[neighbor.id] = self._build_context(
                        neighbor,
                        neighbor_score,
                        self._chunk_metadata(neighbor, folder_value, is_neighbor=True),
                    )

        contexts = sorted(
            contexts_by_chunk_id.values(),
            key=lambda context: (context.similarity_score, -context.chunk_index),
            reverse=True,
        )
        max_contexts = max(top_k, 8)
        return contexts

    def format_context_for_llm(self, contexts: List[RetrieverContext]) -> str:
        """
        Format retrieved contexts into a prompt-ready block.

        The output groups chunks by document and tags each chunk with its index
        so prompt builders can inject it directly into the RAG context window.
        """
        if not contexts:
            return ""

        lines: List[str] = []
        current_document_id: Optional[UUID] = None

        for context in contexts:
            if current_document_id != context.document_id:
                current_document_id = context.document_id
                lines.append(f"[Document {current_document_id}]")

            lines.append(
                f"[Chunk {context.chunk_index} | Score {context.similarity_score:.4f} | Version {context.version}]"
            )
            lines.append(context.chunk_text.strip())
            lines.append("")

        return "\n".join(lines).strip()


__all__ = ["RetrieverContext", "SemanticRetriever"]
