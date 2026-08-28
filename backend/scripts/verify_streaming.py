#!/usr/bin/env python3
import asyncio
import json
import time
import uuid
from datetime import datetime

import httpx
from httpx import AsyncClient
from httpx._transports.asgi import ASGITransport

from app.main import app
from app.api.deps import get_current_user
from app.core.database import async_session_factory
from app.users.services import UserService
from app.users.schemas import ProfileCreate
from app.chat.repositories import ChatMessageRepository, ChatSessionRepository


async def ensure_profile(profile_id: uuid.UUID, email: str):
    async with async_session_factory() as session:
        profile = await UserService.get_profile_by_id(session, profile_id)
        if profile is None:
            print(f"Creating profile {profile_id} {email}")
            schema = ProfileCreate(id=profile_id, email=email, name="Verify Stream", avatar_url=None)
            await UserService.register_profile(session, schema)
            print("Profile created")
        else:
            print(f"Profile {profile_id} already exists")


async def main():
    test_profile_id = uuid.uuid4()
    test_email = f"verify+{test_profile_id.hex[:8]}@example.com"

    # Ensure profile exists in DB
    await ensure_profile(test_profile_id, test_email)

    # Override dependency
    async def _fake_current_user():
        return {"profile_id": str(test_profile_id), "email": test_email, "user_metadata": {}}

    app.dependency_overrides[get_current_user] = _fake_current_user

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver", timeout=None) as client:
        # Create a session via non-streaming endpoint
        print("Creating chat session (non-streaming)")
        r = await client.post("/api/v1/chat/sessions", json={"title": "Verify Stream Session"})
        r.raise_for_status()
        session_obj = r.json()
        session_id = session_obj["id"]
        print("Created session:", session_id)

        # Stream a message and print raw SSE lines with timestamps
        stream_url = f"/api/v1/chat/sessions/{session_id}/messages/stream"
        payload = {"content": "Explain the binary search algorithm briefly and give a short Python example."}
        print("Starting streaming POST to:", stream_url)
        async with client.stream("POST", stream_url, json=payload) as resp:
            print("Status code:", resp.status_code)
            if resp.status_code != 200:
                text = await resp.aread()
                print("Non-200 response body:", text)
                return
            done_metadata = None
            partial_lines = []
            print("--- Begin SSE stream ---")
            async for line in resp.aiter_lines():
                ts = datetime.utcnow().isoformat() + "Z"
                print(f"[{ts}] RAW: {line}")
                if not line:
                    continue
                if line.startswith("data:"):
                    data_raw = line[len("data:"):].strip()
                    try:
                        data = json.loads(data_raw)
                    except Exception as e:
                        print("Failed to parse JSON data in SSE line:", e, data_raw)
                        continue
                    print(f"[{ts}] EVENT: {data}")
                    if data.get("type") == "done":
                        done_metadata = data
                        break
            print("--- End SSE stream ---")

        if not done_metadata:
            print("No done metadata received in stream")
            return

        message_id = done_metadata.get("message_id")
        print("Done metadata message_id:", message_id)

        # Query DB for persisted assistant message
        async with async_session_factory() as session:
            messages = await ChatMessageRepository.get_session_messages(session=session, session_id=uuid.UUID(session_id), profile_id=test_profile_id)
            found = None
            for m in messages:
                if str(m.id) == message_id:
                    found = m
                    break
            if found:
                print("Persisted assistant message:")
                print("id:", found.id)
                print("role:", found.role)
                print("created_at:", found.created_at)
                print("prompt_tokens:", found.prompt_tokens)
                print("completion_tokens:", found.completion_tokens)
                print("citations:", found.citations)
                print("content (truncated 1000 chars):")
                print(found.content[:1000])
            else:
                print("Could not find persisted message with id", message_id)

        # Verify non-streaming endpoint still works
        print("Testing non-streaming endpoint for the same session")
        r2 = await client.post(f"/api/v1/chat/sessions/{session_id}/messages", json={"content": "A short follow-up question: What is the time complexity?"})
        print("Non-streaming status:", r2.status_code)
        if r2.status_code == 201:
            print("Non-streaming response body:", r2.json())
        else:
            print("Non-streaming response body:", await r2.aread())

        # Cleanup: delete the session and messages created
        print("Cleaning up: deleting test session")
        async with async_session_factory() as session:
            chat_session = await ChatSessionRepository.get_session_by_id(session=session, session_id=uuid.UUID(session_id), profile_id=test_profile_id)
            if chat_session:
                await ChatSessionRepository.delete_session(session=session, chat_session=chat_session)
                print("Deleted test session")
            else:
                print("Test session not found for cleanup")


if __name__ == "__main__":
    asyncio.run(main())
