from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.embeddings import generate_query_embedding
from app.documents.models import Document
from app.ingestion.models import DocumentChunk
from app.notes.models import Note, NoteChunk
from app.retrieval.retriever import SemanticRetriever
from app.notes.retriever import NoteRetriever
from app.retrieval.schemas import SearchRequest, SearchResponse, SearchResultItem


class HybridSearchService:
    """Service performing hybrid search (vector cosine similarity + full-text keyword matching)
    across both user-uploaded Documents and user-authored Notes.
    """

    def __init__(
        self,
        document_retriever: Optional[SemanticRetriever] = None,
        note_retriever: Optional[NoteRetriever] = None,
    ) -> None:
        self._doc_retriever = document_retriever or SemanticRetriever()
        self._note_retriever = note_retriever or NoteRetriever()

    @staticmethod
    def _create_snippet(text: str, query: str, max_length: int = 240) -> str:
        """Create a contextual snippet centered around matching query terms if found."""
        if not text:
            return ""
        clean_text = " ".join(text.split())
        query_terms = [t.lower() for t in query.split() if len(t) > 2]

        match_idx = -1
        for term in query_terms:
            idx = clean_text.lower().find(term)
            if idx != -1:
                match_idx = idx
                break

        if match_idx == -1:
            if len(clean_text) <= max_length:
                return clean_text
            return clean_text[:max_length].rstrip() + "..."

        start = max(0, match_idx - max_length // 3)
        end = min(len(clean_text), start + max_length)
        snippet = clean_text[start:end].strip()

        prefix = "..." if start > 0 else ""
        suffix = "..." if end < len(clean_text) else ""
        return f"{prefix}{snippet}{suffix}"

    async def search(
        self,
        session: AsyncSession,
        profile_id: UUID,
        request: SearchRequest,
    ) -> SearchResponse:
        """Perform hybrid search across documents and notes with reciprocal rank fusion."""
        query = request.query.strip()
        if not query:
            return SearchResponse(query=query, results=[], total_count=0)

        source_type = (request.source_type or "all").lower()
        include_docs = source_type in ("all", "document", "documents")
        include_notes = source_type in ("all", "note", "notes")

        # 1. Semantic Vector Search
        try:
            query_embedding = generate_query_embedding(query)
        except Exception:
            query_embedding = []

        semantic_doc_hits = []
        if include_docs and query_embedding:
            try:
                semantic_doc_hits = await self._doc_retriever.retrieve_relevant_chunks(
                    session=session,
                    query_embedding=query_embedding,
                    profile_id=profile_id,
                    folder_id=request.folder_id,
                    top_k=request.top_k * 2,
                    score_threshold=request.score_threshold,
                )
            except Exception:
                semantic_doc_hits = []

        semantic_note_hits = []
        if include_notes and query_embedding:
            try:
                semantic_note_hits = await self._note_retriever.retrieve_relevant_chunks(
                    session=session,
                    query_embedding=query_embedding,
                    profile_id=profile_id,
                    folder_id=request.folder_id,
                    top_k=request.top_k * 2,
                    score_threshold=request.score_threshold,
                )
            except Exception:
                semantic_note_hits = []

        # 2. Keyword Search in PostgreSQL
        keyword_doc_hits: List[Tuple[DocumentChunk, Document]] = []
        if include_docs:
            doc_kw_query = (
                select(DocumentChunk, Document)
                .join(Document, DocumentChunk.document_id == Document.id)
                .where(
                    Document.profile_id == profile_id,
                    Document.is_deleted == False,
                    (DocumentChunk.chunk_text.ilike(f"%{query}%") | Document.name.ilike(f"%{query}%")),
                )
            )
            if request.folder_id is not None:
                doc_kw_query = doc_kw_query.where(Document.folder_id == request.folder_id)
            doc_kw_query = doc_kw_query.limit(request.top_k * 2)

            res = await session.execute(doc_kw_query)
            keyword_doc_hits = res.all()

        keyword_note_hits: List[Tuple[NoteChunk, Note]] = []
        if include_notes:
            note_kw_query = (
                select(NoteChunk, Note)
                .join(Note, NoteChunk.note_id == Note.id)
                .where(
                    Note.profile_id == profile_id,
                    (NoteChunk.chunk_text.ilike(f"%{query}%") | Note.title.ilike(f"%{query}%")),
                )
            )
            if request.folder_id is not None and hasattr(Note, "folder_id"):
                note_kw_query = note_kw_query.where(Note.folder_id == request.folder_id)
            note_kw_query = note_kw_query.limit(request.top_k * 2)

            res = await session.execute(note_kw_query)
            keyword_note_hits = res.all()

        # Cache document titles for semantic hits
        doc_titles: Dict[UUID, str] = {}
        if semantic_doc_hits:
            doc_ids = list({ctx.document_id for ctx in semantic_doc_hits})
            doc_stmt = select(Document.id, Document.name).where(Document.id.in_(doc_ids))
            doc_res = await session.execute(doc_stmt)
            for d_id, d_name in doc_res.all():
                doc_titles[d_id] = d_name

        # 3. Reciprocal Rank Fusion (RRF)
        # Unique keys: (source_type, chunk_id)
        RRF_K = 60
        scores: Dict[Tuple[str, UUID], float] = {}
        item_data: Dict[Tuple[str, UUID], dict] = {}

        # Process Semantic Doc Hits
        for rank, hit in enumerate(semantic_doc_hits):
            key = ("document", hit.chunk_id)
            rrf_contrib = 1.0 / (RRF_K + rank + 1)
            scores[key] = scores.get(key, 0.0) + rrf_contrib
            if key not in item_data:
                item_data[key] = {
                    "id": hit.chunk_id,
                    "parent_id": hit.document_id,
                    "title": doc_titles.get(hit.document_id, "Document"),
                    "snippet": self._create_snippet(hit.chunk_text, query),
                    "source_type": "document",
                    "chunk_index": hit.chunk_index,
                    "similarity_score": hit.similarity_score,
                    "folder_id": request.folder_id,
                }
            else:
                item_data[key]["similarity_score"] = max(item_data[key]["similarity_score"], hit.similarity_score)

        # Process Semantic Note Hits
        for rank, hit in enumerate(semantic_note_hits):
            key = ("note", hit.chunk_id)
            rrf_contrib = 1.0 / (RRF_K + rank + 1)
            scores[key] = scores.get(key, 0.0) + rrf_contrib
            if key not in item_data:
                item_data[key] = {
                    "id": hit.chunk_id,
                    "parent_id": hit.note_id,
                    "title": hit.note_title or "Quick Note",
                    "snippet": self._create_snippet(hit.chunk_text, query),
                    "source_type": "note",
                    "chunk_index": hit.chunk_index,
                    "similarity_score": hit.similarity_score,
                    "folder_id": request.folder_id,
                }
            else:
                item_data[key]["similarity_score"] = max(item_data[key]["similarity_score"], hit.similarity_score)

        # Process Keyword Doc Hits
        for rank, (chunk, doc) in enumerate(keyword_doc_hits):
            key = ("document", chunk.id)
            rrf_contrib = 1.0 / (RRF_K + rank + 1)
            scores[key] = scores.get(key, 0.0) + rrf_contrib
            if key not in item_data:
                item_data[key] = {
                    "id": chunk.id,
                    "parent_id": doc.id,
                    "title": getattr(doc, "name", getattr(doc, "title", "Document")),
                    "snippet": self._create_snippet(chunk.chunk_text, query),
                    "source_type": "document",
                    "chunk_index": chunk.chunk_index,
                    "similarity_score": 0.75,  # keyword baseline score
                    "folder_id": doc.folder_id,
                }
            else:
                # boost similarity score for items matching both vector and keyword
                item_data[key]["similarity_score"] = min(1.0, item_data[key]["similarity_score"] + 0.1)

        # Process Keyword Note Hits
        for rank, (chunk, note) in enumerate(keyword_note_hits):
            key = ("note", chunk.id)
            rrf_contrib = 1.0 / (RRF_K + rank + 1)
            scores[key] = scores.get(key, 0.0) + rrf_contrib
            if key not in item_data:
                item_data[key] = {
                    "id": chunk.id,
                    "parent_id": note.id,
                    "title": note.title or "Quick Note",
                    "snippet": self._create_snippet(chunk.chunk_text, query),
                    "source_type": "note",
                    "chunk_index": chunk.chunk_index,
                    "similarity_score": 0.75,  # keyword baseline score
                    "folder_id": getattr(note, "folder_id", None),
                }
            else:
                item_data[key]["similarity_score"] = min(1.0, item_data[key]["similarity_score"] + 0.1)

        # Sort items by combined RRF score with similarity_score as tie-breaker
        sorted_keys = sorted(
            scores.keys(),
            key=lambda k: (scores[k], item_data[k].get("similarity_score", 0.0)),
            reverse=True,
        )

        results: List[SearchResultItem] = []
        for k in sorted_keys[:request.top_k]:
            data = item_data[k]
            results.append(SearchResultItem.model_validate(data))

        return SearchResponse(
            query=query,
            results=results,
            total_count=len(sorted_keys),
        )


__all__ = ["HybridSearchService"]
