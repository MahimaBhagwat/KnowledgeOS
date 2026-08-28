"""
Vector store integration for KnowledgeOS document embeddings.

This module bridges PostgreSQL document chunks and ChromaDB vector storage
using chunk UUIDs as the vector identifiers.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List, Optional, Sequence
from uuid import UUID

from app.core.config import settings
from app.ingestion.models import DocumentChunk


class VectorStoreManager:
    """
    Manage ChromaDB persistence for document chunk embeddings.

    The manager uses a persistent Chroma client backed by the application
    configured CHROMA_PERSIST_DIRECTORY. A single collection is used for all
    document chunks, with metadata filters enforcing tenant isolation.
    """

    def __init__(self, collection_name: str = "document_chunks") -> None:
        self._collection_name = collection_name
        self._client = self._build_client()
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    @staticmethod
    @lru_cache(maxsize=1)
    def _build_client() -> Any:
        """
        Build and cache the persistent Chroma client.

        The application settings already validate that the persistence
        directory exists, so we can safely initialize the client here.
        """
        try:
            import chromadb
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "chromadb is required to initialize the vector store."
            ) from exc

        return chromadb.PersistentClient(
            path=str(settings.chroma_persist_directory)
        )

    @staticmethod
    def _safe_chunk_metadata(chunk: DocumentChunk) -> Dict[str, object]:
        """
        Build metadata for a chunk using fields supported by ChromaDB.

        The current document chunk model stores the core retrieval fields.
        This helper also captures optional source fields when present on the
        model instance so future schema extensions are automatically included.
        """
        metadata: Dict[str, object] = {
            "chunk_id": str(chunk.id),
            "document_id": str(chunk.document_id),
            "profile_id": str(chunk.profile_id),
            "chunk_index": int(chunk.chunk_index),
            "version": int(chunk.version),
            "token_count": int(chunk.token_count),
            "overlap_tokens": int(chunk.overlap_tokens),
            "embedding_status": str(
                getattr(chunk, "embedding_status", None) or "pending"
            ),
        }

        optional_uuid_fields = (
            "previous_chunk_id",
            "next_chunk_id",
            "folder_id",
        )
        optional_int_fields = (
            "start_character",
            "end_character",
            "page_number",
            "paragraph_number",
        )
        optional_text_fields = (
            "heading_path",
            "document_type",
            "source_type",
            "language",
        )

        for field_name in optional_uuid_fields:
            value = getattr(chunk, field_name, None)
            if value is not None:
                metadata[field_name] = str(value)

        for field_name in optional_int_fields:
            value = getattr(chunk, field_name, None)
            if value is not None:
                metadata[field_name] = int(value)

        for field_name in optional_text_fields:
            value = getattr(chunk, field_name, None)
            if value is not None:
                metadata[field_name] = str(value)

        document = getattr(chunk, "document", None)
        if document is not None:
            folder_id = getattr(document, "folder_id", None)
            if folder_id is not None:
                metadata["folder_id"] = str(folder_id)

        return metadata

    @staticmethod
    def _normalize_embeddings(
        embeddings: Sequence[Sequence[float]],
    ) -> List[List[float]]:
        """
        Normalize embeddings to Chroma-friendly float lists.
        """
        return [[float(value) for value in vector] for vector in embeddings]

    def add_document_chunks(
        self,
        document_id: UUID,
        profile_id: UUID,
        chunks: List[DocumentChunk],
        embeddings: Optional[List[List[float]]] = None,
    ) -> None:
        """
        Add document chunks and embeddings to ChromaDB.

        Embeddings must be supplied by the caller or a dedicated embedding
        pipeline. The ingestion architecture stores pre-computed embeddings
        rather than generating them inside the vector store.
        """
        if not chunks:
            return

        if embeddings is None:
            raise ValueError(
                "Embeddings are required to add document chunks to the vector store."
            )

        if len(embeddings) != len(chunks):
            raise ValueError(
                "Embeddings count must match the number of document chunks."
            )

        normalized_embeddings = self._normalize_embeddings(embeddings)
        ids = [str(chunk.id) for chunk in chunks]
        texts = [chunk.chunk_text for chunk in chunks]
        metadatas = [self._safe_chunk_metadata(chunk) for chunk in chunks]

        for metadata, chunk in zip(metadatas, chunks):
            metadata["document_id"] = str(document_id)
            metadata["profile_id"] = str(profile_id)
            metadata["chunk_id"] = str(chunk.id)

        self._collection.upsert(
            ids=ids,
            documents=texts,
            metadatas=metadatas,
            embeddings=normalized_embeddings,
        )

    def similarity_search(
        self,
        query_embedding: List[float],
        profile_id: UUID,
        top_k: int = 5,
        folder_id: Optional[UUID] = None,
    ) -> List[dict]:
        """
        Perform a metadata-filtered similarity search over ChromaDB.

        The query is always scoped to the authenticated profile_id. When a
        folder_id is provided, it is included as an additional metadata filter
        so higher-level callers can scope retrieval to a virtual collection.
        """
        if top_k <= 0:
            raise ValueError("top_k must be greater than zero.")

        if folder_id is not None:
            where: Dict[str, object] = {
                "$and": [
                    {"profile_id": str(profile_id)},
                    {"folder_id": str(folder_id)},
                ]
            }
        else:
            where = {"profile_id": str(profile_id)}

        result = self._collection.query(
            query_embeddings=[self._normalize_embeddings([query_embedding])[0]],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        search_results: List[dict] = []
        for index, vector_id in enumerate(ids):
            metadata = metadatas[index] if index < len(metadatas) else {}
            document_text = documents[index] if index < len(documents) else ""
            distance = distances[index] if index < len(distances) else None

            search_results.append(
                {
                    "id": vector_id,
                    "document": document_text,
                    "metadata": metadata,
                    "distance": distance,
                }
            )

        return search_results

    def delete_document_vectors(self, document_id: UUID) -> None:
        """
        Remove all vectors associated with a document from ChromaDB.
        """
        self._collection.delete(where={"document_id": str(document_id)})

    @staticmethod
    def _safe_note_chunk_metadata(
        chunk: Any,
        folder_id: Optional[UUID] = None,
        note_title: Optional[str] = None,
    ) -> Dict[str, object]:
        """
        Build ChromaDB metadata for a note chunk tagged with source_type='note'.
        """
        metadata: Dict[str, object] = {
            "chunk_id": str(chunk.id),
            "note_id": str(chunk.note_id),
            "profile_id": str(chunk.profile_id),
            "source_type": "note",
            "chunk_index": int(chunk.chunk_index),
            "version": int(getattr(chunk, "version", 1)),
            "token_count": int(chunk.token_count),
            "overlap_tokens": int(getattr(chunk, "overlap_tokens", 0)),
            "embedding_status": str(
                getattr(chunk, "embedding_status", None) or "ready"
            ),
        }

        resolved_folder_id = folder_id or getattr(chunk, "folder_id", None)
        if resolved_folder_id is not None:
            metadata["folder_id"] = str(resolved_folder_id)

        if note_title:
            metadata["title"] = str(note_title)

        if getattr(chunk, "previous_chunk_id", None) is not None:
            metadata["previous_chunk_id"] = str(chunk.previous_chunk_id)

        if getattr(chunk, "next_chunk_id", None) is not None:
            metadata["next_chunk_id"] = str(chunk.next_chunk_id)

        if getattr(chunk, "start_character", None) is not None:
            metadata["start_character"] = int(chunk.start_character)

        if getattr(chunk, "end_character", None) is not None:
            metadata["end_character"] = int(chunk.end_character)

        return metadata

    def add_note_chunks(
        self,
        note_id: UUID,
        profile_id: UUID,
        chunks: List[Any],
        embeddings: Optional[List[List[float]]] = None,
        folder_id: Optional[UUID] = None,
        note_title: Optional[str] = None,
    ) -> None:
        """
        Add note chunks and embeddings to ChromaDB tagged with source_type='note'.
        """
        if not chunks:
            return

        if embeddings is None:
            raise ValueError(
                "Embeddings are required to add note chunks to the vector store."
            )

        if len(embeddings) != len(chunks):
            raise ValueError(
                "Embeddings count must match the number of note chunks."
            )

        normalized_embeddings = self._normalize_embeddings(embeddings)
        ids = [str(chunk.id) for chunk in chunks]
        texts = [chunk.chunk_text for chunk in chunks]
        metadatas = [
            self._safe_note_chunk_metadata(chunk, folder_id=folder_id, note_title=note_title)
            for chunk in chunks
        ]

        for metadata in metadatas:
            metadata["note_id"] = str(note_id)
            metadata["profile_id"] = str(profile_id)
            metadata["source_type"] = "note"

        self._collection.upsert(
            ids=ids,
            documents=texts,
            metadatas=metadatas,
            embeddings=normalized_embeddings,
        )

    def similarity_search_notes(
        self,
        query_embedding: List[float],
        profile_id: UUID,
        top_k: int = 5,
        folder_id: Optional[UUID] = None,
    ) -> List[dict]:
        """
        Perform a metadata-filtered similarity search for user notes in ChromaDB.
        Filters strictly on profile_id and source_type: "note".
        """
        if top_k <= 0:
            raise ValueError("top_k must be greater than zero.")

        if folder_id is not None:
            where: Dict[str, object] = {
                "$and": [
                    {"profile_id": str(profile_id)},
                    {"source_type": "note"},
                    {"folder_id": str(folder_id)},
                ]
            }
        else:
            where = {
                "$and": [
                    {"profile_id": str(profile_id)},
                    {"source_type": "note"},
                ]
            }

        result = self._collection.query(
            query_embeddings=[self._normalize_embeddings([query_embedding])[0]],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        search_results: List[dict] = []
        for index, vector_id in enumerate(ids):
            metadata = metadatas[index] if index < len(metadatas) else {}
            document_text = documents[index] if index < len(documents) else ""
            distance = distances[index] if index < len(distances) else None

            search_results.append(
                {
                    "id": vector_id,
                    "document": document_text,
                    "metadata": metadata,
                    "distance": distance,
                }
            )

        return search_results

    def delete_note_vectors(self, note_id: UUID) -> None:
        """
        Remove all vectors associated with a note from ChromaDB.
        """
        self._collection.delete(where={"note_id": str(note_id)})

