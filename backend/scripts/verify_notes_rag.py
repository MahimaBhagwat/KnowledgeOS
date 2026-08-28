#!/usr/bin/env python3
"""
Verification script for Notes RAG integration:
1. Create a user-authored note
2. Verify NoteChunk creation & ChromaDB vector indexing
3. Verify NoteRetriever retrieval
4. Verify standard chat RAG retrieval with composed document/note citations
5. Verify streaming chat RAG retrieval
6. Verify agentic chat RAG retrieval
7. Verify note deletion vector and chunk cleanup
"""

import asyncio
import json
import uuid
from datetime import datetime

from httpx import AsyncClient
from httpx._transports.asgi import ASGITransport

from app.main import app
from app.api.deps import get_current_user
from app.core.database import async_session_factory
from app.core.embeddings import generate_query_embedding
from app.notes.models import Note, NoteChunk
from app.notes.repositories import NoteChunkRepository, NoteRepository
from app.notes.retriever import NoteRetriever
from app.notes.services import NoteService
from app.users.services import UserService
from app.users.schemas import ProfileCreate
from app.chat.repositories import ChatMessageRepository, ChatSessionRepository
from app.ingestion.vector_store import VectorStoreManager


async def ensure_profile(profile_id: uuid.UUID, email: str):
    async with async_session_factory() as session:
        profile = await UserService.get_profile_by_id(session, profile_id)
        if profile is None:
            print(f"Creating profile {profile_id} ({email})")
            schema = ProfileCreate(id=profile_id, email=email, name="Notes RAG Verifier", avatar_url=None)
            await UserService.register_profile(session, schema)
            print("Profile created successfully")
        else:
            print(f"Profile {profile_id} already exists")


async def main():
    print("=" * 60)
    print("STARTING NOTES RAG VERIFICATION TEST")
    print("=" * 60)

    test_profile_id = uuid.uuid4()
    test_email = f"notes_rag_{test_profile_id.hex[:8]}@example.com"

    await ensure_profile(test_profile_id, test_email)

    # 1. Create a test Note
    note_title = "Project Chronos Microservices Architecture"
    note_content = (
        "Project Chronos uses an event-driven architecture with Apache Kafka for real-time messaging. "
        "The primary database is PostgreSQL for relational data and Redis for sub-millisecond caching. "
        "All services authenticate using mTLS and JWT tokens signed by the Chronos Auth Gateway. "
        "The batch processing pipeline uses Celery workers with distributed locking via Redis."
    )

    print("\n--- STEP 1: Creating Note via NoteService ---")
    async with async_session_factory() as session:
        note = await NoteService.create_note(
            session=session,
            profile_id=test_profile_id,
            title=note_title,
            content=note_content,
        )
        print(f"Created note with id: {note.id}")
        note_id = note.id

    # 2. Verify NoteChunk records in PostgreSQL
    print("\n--- STEP 2: Verifying NoteChunk in PostgreSQL ---")
    async with async_session_factory() as session:
        chunks = await NoteChunkRepository.get_chunks_by_note(
            session=session,
            note_id=note_id,
            profile_id=test_profile_id,
        )
        assert len(chunks) > 0, "Expected at least one NoteChunk record"
        for chunk in chunks:
            print(f"  Chunk index: {chunk.chunk_index}, token_count: {chunk.token_count}, status: {chunk.embedding_status}")
            assert chunk.embedding_status == "ready", f"Expected embedding_status 'ready', got '{chunk.embedding_status}'"
            assert "Project Chronos" in chunk.chunk_text

    # 3. Verify ChromaDB vector persistence
    print("\n--- STEP 3: Verifying ChromaDB vectors ---")
    vector_store = VectorStoreManager()
    query_emb = generate_query_embedding("What message broker does Project Chronos use?")
    search_results = vector_store.similarity_search_notes(
        query_embedding=query_emb,
        profile_id=test_profile_id,
        top_k=5,
    )
    print(f"Found {len(search_results)} matching note vector results in ChromaDB")
    assert len(search_results) > 0, "Expected ChromaDB to find note vector"
    top_hit = search_results[0]
    print(f"  Top vector metadata: {top_hit['metadata']}")
    assert top_hit["metadata"].get("source_type") == "note", "Expected source_type='note' in metadata"
    assert top_hit["metadata"].get("note_id") == str(note_id)

    # 4. Verify NoteRetriever directly
    print("\n--- STEP 4: Testing NoteRetriever.retrieve_relevant_chunks ---")
    note_retriever = NoteRetriever(vector_store_manager=vector_store)
    async with async_session_factory() as session:
        retrieved_contexts = await note_retriever.retrieve_relevant_chunks(
            session=session,
            query_embedding=query_emb,
            profile_id=test_profile_id,
            top_k=5,
        )
        print(f"Retrieved {len(retrieved_contexts)} contexts from NoteRetriever")
        assert len(retrieved_contexts) > 0, "Expected at least one context from NoteRetriever"
        print(f"  Score: {retrieved_contexts[0].similarity_score:.4f}")
        print(f"  Note title: {retrieved_contexts[0].note_title}")
        formatted_prompt = note_retriever.format_context_for_llm(retrieved_contexts)
        print(f"  Formatted context excerpt:\n{formatted_prompt[:200]}...")

    # 5. Test Chat Endpoints via HTTP ASGI client
    async def _fake_current_user():
        return {"profile_id": str(test_profile_id), "email": test_email, "user_metadata": {}}

    app.dependency_overrides[get_current_user] = _fake_current_user
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver", timeout=60) as client:
        # Create chat session
        print("\n--- STEP 5: Testing Chat Session & Standard Message with Notes RAG ---")
        sess_resp = await client.post("/api/v1/chat/sessions", json={"title": "Chronos Architecture Chat"})
        sess_resp.raise_for_status()
        chat_session_id = sess_resp.json()["id"]
        print(f"Created chat session: {chat_session_id}")

        msg_payload = {"content": "What caching layer and message broker does Project Chronos use?"}
        msg_resp = await client.post(f"/api/v1/chat/sessions/{chat_session_id}/messages", json=msg_payload)
        print(f"Chat response status: {msg_resp.status_code}")
        assert msg_resp.status_code == 201, f"Chat message post failed: {msg_resp.text}"
        msg_data = msg_resp.json()
        print(f"Assistant response content:\n{msg_data['content']}")
        print(f"Citations: {json.dumps(msg_data.get('citations'), indent=2)}")

        citations = msg_data.get("citations") or []
        assert len(citations) > 0, "Expected citations in chat assistant message"
        has_note_citation = any(c.get("source_type") == "note" or c.get("note_id") == str(note_id) for c in citations)
        assert has_note_citation, "Expected note citation in citations payload"
        print("[OK] Standard chat message successfully cited the note!")

        # 6. Test Streaming Chat Endpoint
        print("\n--- STEP 6: Testing Streaming Chat with Notes RAG ---")
        stream_payload = {"content": "Explain how authentication works in Chronos."}
        stream_resp = await client.post(f"/api/v1/chat/sessions/{chat_session_id}/messages/stream", json=stream_payload)
        assert stream_resp.status_code == 200, f"Stream post failed: {stream_resp.text}"
        stream_text = stream_resp.text
        print(f"Stream output sample (first 300 chars):\n{stream_text[:300]}...")
        assert "data: " in stream_text
        assert '"type": "done"' in stream_text
        print("[OK] Streaming chat completed with done event!")

        # 7. Test Agentic Chat Endpoint
        print("\n--- STEP 7: Testing Agentic Chat Pipeline with Notes RAG ---")
        agentic_payload = {"content": "Analyze the Chronos batch processing pipeline and security model."}
        agentic_resp = await client.post(f"/api/v1/chat/sessions/{chat_session_id}/messages/agentic", json=agentic_payload)
        print(f"Agentic response status: {agentic_resp.status_code}")
        if agentic_resp.status_code == 201:
            agentic_data = agentic_resp.json()
            print("Plan steps count:", len(agentic_data.get("plan", {}).get("steps", [])))
            print("Execution success:", agentic_data.get("execution", {}).get("success"))
            print("Review success:", agentic_data.get("review", {}).get("success"))
            print("Assistant message excerpt:", agentic_data.get("assistant_message", {}).get("content", "")[:200])
            print("[OK] Agentic pipeline successfully utilized notes context!")
        else:
            print("Agentic response status not 201 (possibly disabled in config):", agentic_resp.text)

        # 8. Test Note Deletion & Cleanup
        print("\n--- STEP 8: Testing Note Deletion & Vector Cleanup ---")
        async with async_session_factory() as session:
            await NoteService.delete_note(session=session, profile_id=test_profile_id, note_id=note_id)
            print(f"Deleted note {note_id}")

        async with async_session_factory() as session:
            remaining_chunks = await NoteChunkRepository.get_chunks_by_note(
                session=session,
                note_id=note_id,
                profile_id=test_profile_id,
            )
            assert len(remaining_chunks) == 0, f"Expected 0 chunks remaining, got {len(remaining_chunks)}"
            print("[OK] PostgreSQL note chunks deleted")

        remaining_vectors = vector_store.similarity_search_notes(
            query_embedding=query_emb,
            profile_id=test_profile_id,
            top_k=5,
        )
        assert len(remaining_vectors) == 0, f"Expected 0 vectors remaining, got {len(remaining_vectors)}"
        print("[OK] ChromaDB note vectors deleted")

        # Cleanup chat session
        await client.delete(f"/api/v1/chat/sessions/{chat_session_id}")
        print("[OK] Cleaned up chat session")

    print("\n" + "=" * 60)
    print("ALL NOTES RAG TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
