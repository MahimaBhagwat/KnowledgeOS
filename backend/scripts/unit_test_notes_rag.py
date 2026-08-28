#!/usr/bin/env python3
"""
Unit test suite for Notes RAG components:
- NoteChunk model structure
- ChunkData -> NoteChunk field mapping
- VectorStoreManager note metadata & query filters
- NoteRetriever formatting & context generation
- Composed ChatService context orchestration & citations formatting
- CitationOut schema validation
- Alembic migration revision verification
"""

import os
import sys
import tempfile
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# Setup mock environment before app imports
temp_chroma = tempfile.mkdtemp()
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/testdb")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-key")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-jwt-secret")
os.environ.setdefault("SUPABASE_STORAGE_BUCKET", "test-bucket")
os.environ.setdefault("CHROMA_PERSIST_DIRECTORY", temp_chroma)
os.environ.setdefault("LLM_PROVIDER", "litellm")
os.environ.setdefault("LLM_API_KEY", "test-api-key")
os.environ.setdefault("LLM_CHAT_MODEL_NAME", "gpt-4o-mini")
os.environ.setdefault("LLM_EMBEDDING_MODEL_NAME", "text-embedding-3-small")

# Ensure backend package is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.ingestion.chunker import TextChunker, ChunkData
from app.notes.models import Note, NoteChunk
from app.notes.repositories import NoteChunkRepository, NoteRepository
from app.notes.retriever import NoteRetriever, NoteRetrieverContext
from app.chat.schemas import CitationOut
from app.ingestion.vector_store import VectorStoreManager


def test_note_chunk_model():
    print("Testing NoteChunk model schema...")
    assert NoteChunk.__tablename__ == "note_chunks"
    columns = {c.name: c for c in NoteChunk.__table__.columns}
    required_cols = [
        "id", "note_id", "profile_id", "chunk_index", "chunk_text",
        "token_count", "overlap_tokens", "start_character", "end_character",
        "previous_chunk_id", "next_chunk_id", "version", "embedding_status"
    ]
    for col in required_cols:
        assert col in columns, f"Missing column {col} in NoteChunk"
    print("[OK] NoteChunk model schema verified")


def test_chunker_compatibility():
    print("\nTesting TextChunker output compatibility...")
    sample_text = (
        "KnowledgeOS is an intelligent workspace.\n\n"
        "It supports Documents, Folders, Chat, and Quick Notes.\n\n"
        "This note explains how Notes are integrated into RAG."
    )
    chunker = TextChunker(target_chunk_tokens=50, target_chunk_characters=200)
    chunks = chunker.create_chunks(sample_text)
    assert len(chunks) > 0
    first_chunk = chunks[0]
    assert isinstance(first_chunk, ChunkData)
    assert hasattr(first_chunk, "chunk_index")
    assert hasattr(first_chunk, "chunk_text")
    assert hasattr(first_chunk, "token_count")
    assert hasattr(first_chunk, "overlap_tokens")
    assert hasattr(first_chunk, "start_character")
    assert hasattr(first_chunk, "end_character")
    assert first_chunk.chunk_index == 0
    assert first_chunk.token_count > 0
    print("[OK] TextChunker output fields verified exactly matching ChunkData contract")


def test_vector_store_note_metadata():
    print("\nTesting VectorStoreManager note metadata...")
    note_id = uuid.uuid4()
    profile_id = uuid.uuid4()
    chunk_id = uuid.uuid4()
    folder_id = uuid.uuid4()

    mock_chunk = MagicMock()
    mock_chunk.id = chunk_id
    mock_chunk.note_id = note_id
    mock_chunk.profile_id = profile_id
    mock_chunk.chunk_index = 0
    mock_chunk.version = 1
    mock_chunk.token_count = 42
    mock_chunk.overlap_tokens = 5
    mock_chunk.embedding_status = "ready"
    mock_chunk.previous_chunk_id = None
    mock_chunk.next_chunk_id = None
    mock_chunk.start_character = 0
    mock_chunk.end_character = 100

    meta = VectorStoreManager._safe_note_chunk_metadata(
        chunk=mock_chunk,
        folder_id=folder_id,
        note_title="Test Title",
    )

    assert meta["chunk_id"] == str(chunk_id)
    assert meta["note_id"] == str(note_id)
    assert meta["profile_id"] == str(profile_id)
    assert meta["source_type"] == "note"
    assert meta["chunk_index"] == 0
    assert meta["folder_id"] == str(folder_id)
    assert meta["title"] == "Test Title"
    print("[OK] VectorStoreManager note metadata generation verified")


def test_note_retriever_formatting():
    print("\nTesting NoteRetriever formatting...")
    note_id = uuid.uuid4()
    chunk_id = uuid.uuid4()
    ctx = NoteRetrieverContext(
        chunk_id=chunk_id,
        note_id=note_id,
        chunk_index=0,
        chunk_text="KnowledgeOS architecture is modular.",
        similarity_score=0.92,
        version=1,
        metadata={"source_type": "note"},
        note_title="Architecture Overview",
    )

    retriever = NoteRetriever(vector_store_manager=MagicMock())
    formatted = retriever.format_context_for_llm([ctx])
    assert f"[Note {note_id} - \"Architecture Overview\"]" in formatted
    assert "[Chunk 0 | Score 0.9200 | Version 1]" in formatted
    assert "KnowledgeOS architecture is modular." in formatted
    print("[OK] NoteRetriever LLM context formatting verified")


def test_citation_out_schema():
    print("\nTesting CitationOut schema with note and document citations...")
    doc_chunk_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    doc_citation = CitationOut(
        chunk_id=doc_chunk_id,
        document_id=doc_id,
        source_type="document",
        chunk_index=0,
        similarity_score=0.88,
        chunk_text="Document chunk text",
    )
    assert doc_citation.source_type == "document"
    assert doc_citation.document_id == doc_id
    assert doc_citation.note_id is None

    note_chunk_id = uuid.uuid4()
    note_id = uuid.uuid4()
    note_citation = CitationOut(
        chunk_id=note_chunk_id,
        document_id=note_id,  # fallback for frontend
        note_id=note_id,
        source_type="note",
        chunk_index=1,
        similarity_score=0.95,
        chunk_text="Note chunk text",
    )
    assert note_citation.source_type == "note"
    assert note_citation.note_id == note_id
    assert note_citation.document_id == note_id
    print("[OK] CitationOut schema backwards and forwards compatibility verified")


def test_alembic_migration():
    print("\nTesting Alembic migration file...")
    import importlib.util
    migration_path = backend_dir / "migrations" / "versions" / "a3c1e2f4b5d6_add_note_chunks_table.py"
    assert migration_path.exists(), f"Migration file {migration_path} does not exist"

    spec = importlib.util.spec_from_file_location("migration_note_chunks", migration_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.revision == "a3c1e2f4b5d6"
    assert module.down_revision == "9ac199d8d97a"
    assert hasattr(module, "upgrade")
    assert hasattr(module, "downgrade")
    print("[OK] Alembic migration revision chain verified")


async def test_chat_composed_retrieval():
    print("\nTesting ChatService composed retrieval...")
    from app.chat.services import ChatService
    from app.retrieval.retriever import RetrieverContext

    mock_doc_retriever = MagicMock()
    doc_chunk_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    doc_ctx = RetrieverContext(
        chunk_id=doc_chunk_id,
        document_id=doc_id,
        chunk_index=0,
        chunk_text="Document content on system design",
        similarity_score=0.85,
        version=1,
        metadata={},
    )
    mock_doc_retriever.retrieve_relevant_chunks = AsyncMock(return_value=[doc_ctx])
    mock_doc_retriever.format_context_for_llm = MagicMock(return_value="[Document 123]\nDocument content on system design")

    mock_note_retriever = MagicMock()
    note_chunk_id = uuid.uuid4()
    note_id = uuid.uuid4()
    note_ctx = NoteRetrieverContext(
        chunk_id=note_chunk_id,
        note_id=note_id,
        chunk_index=0,
        chunk_text="User note content on custom specs",
        similarity_score=0.92,
        version=1,
        metadata={},
        note_title="Custom Specs",
    )
    mock_note_retriever.retrieve_relevant_chunks = AsyncMock(return_value=[note_ctx])
    mock_note_retriever.format_context_for_llm = MagicMock(return_value="[Note 456 - \"Custom Specs\"]\nUser note content on custom specs")

    chat_service = ChatService(
        retriever=mock_doc_retriever,
        note_retriever=mock_note_retriever,
    )

    mock_session = AsyncMock()
    profile_id = uuid.uuid4()

    from unittest.mock import patch
    with patch("app.chat.services.generate_query_embedding", return_value=[0.1, 0.2, 0.3]):
        system_context, citations = await chat_service._retrieve_composed_context(
            session=mock_session,
            query_text="What are the system design and custom specs?",
            profile_id=profile_id,
        )

    assert "--- Document Knowledge ---" in system_context
    assert "--- User Notes ---" in system_context
    assert "[Document 123]" in system_context
    assert "[Note 456 - \"Custom Specs\"]" in system_context

    assert citations is not None
    assert len(citations) == 2
    # Note has higher similarity score (0.92 > 0.85), so it should be first
    assert citations[0]["source_type"] == "note"
    assert citations[0]["similarity_score"] == 0.92
    assert citations[0]["note_id"] == str(note_id)
    assert citations[0]["document_id"] == str(note_id)

    assert citations[1]["source_type"] == "document"
    assert citations[1]["similarity_score"] == 0.85
    assert citations[1]["document_id"] == str(doc_id)

    print("[OK] ChatService composed retrieval, section formatting, and merged citations verified")


async def test_note_ingestion_service():
    print("\nTesting NoteIngestionService and NoteChunkRepository...")
    from app.notes.services import NoteIngestionService
    from unittest.mock import patch

    mock_session = AsyncMock()
    note_id = uuid.uuid4()
    profile_id = uuid.uuid4()
    mock_note = Note(
        id=note_id,
        profile_id=profile_id,
        title="Project Apollo",
        content="Apollo uses GraphQL for client APIs and gRPC for internal service communications.",
    )

    mock_vector_store = MagicMock()
    ingestion_service = NoteIngestionService(vector_store_manager=mock_vector_store)

    with patch("app.notes.services.generate_embeddings", return_value=[[0.1, 0.2, 0.3]]):
        chunks = await ingestion_service.process_note(session=mock_session, note=mock_note)

    assert len(chunks) > 0
    assert chunks[0].note_id == note_id
    assert chunks[0].profile_id == profile_id
    assert "Project Apollo" in chunks[0].chunk_text
    assert mock_vector_store.add_note_chunks.called

    # Test vector & chunk deletion
    await ingestion_service.delete_note_vectors_and_chunks(
        session=mock_session,
        note_id=note_id,
        profile_id=profile_id,
    )
    assert mock_vector_store.delete_note_vectors.called
    print("[OK] NoteIngestionService process_note and delete_note_vectors_and_chunks verified")


if __name__ == "__main__":
    import asyncio
    print("=" * 60)
    print("RUNNING NOTES RAG UNIT TESTS")
    print("=" * 60)
    test_note_chunk_model()
    test_chunker_compatibility()
    test_vector_store_note_metadata()
    test_note_retriever_formatting()
    test_citation_out_schema()
    test_alembic_migration()
    asyncio.run(test_chat_composed_retrieval())
    asyncio.run(test_note_ingestion_service())
    print("\n" + "=" * 60)
    print("ALL UNIT TESTS PASSED!")
    print("=" * 60)

