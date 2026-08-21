#!/usr/bin/env python3
import asyncio
import json
import uuid
from datetime import datetime

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
            schema = ProfileCreate(id=profile_id, email=email, name="Verify Agentic", avatar_url=None)
            await UserService.register_profile(session, schema)
            print("Profile created")
        else:
            print(f"Profile {profile_id} already exists")


async def main():
    test_profile_id = uuid.uuid4()
    test_email = f"verify+{test_profile_id.hex[:8]}@example.com"

    # Ensure profile exists in DB
    await ensure_profile(test_profile_id, test_email)

    # Override dependency to act as this user
    async def _fake_current_user():
        return {"profile_id": str(test_profile_id), "email": test_email, "user_metadata": {}}

    app.dependency_overrides[get_current_user] = _fake_current_user

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver", timeout=600) as client:
        # Create chat session
        print("Creating chat session for agentic test")
        r = await client.post("/api/v1/chat/sessions", json={"title": "Verify Agentic Session"})
        r.raise_for_status()
        session_obj = r.json()
        session_id = session_obj["id"]
        print("Created session:", session_id)

        # Post agentic message
        payload = {"content": "Summarize the README and list three follow-up questions to clarify the project scope."}
        print("Posting to agentic endpoint")
        r2 = await client.post(f"/api/v1/chat/sessions/{session_id}/messages/agentic", json=payload)
        print("Agentic status:", r2.status_code)
        text = await r2.aread()
        try:
            body = r2.json()
        except Exception:
            print("Failed to parse JSON response from agentic endpoint. Raw text:", text)
            return

        print("Agentic response keys:", list(body.keys()))
        print("Plan (truncated):")
        print(json.dumps(body.get("plan"), indent=2)[:2000])
        print("Execution (truncated):")
        print(json.dumps(body.get("execution"), indent=2)[:2000])
        print("Review (truncated):")
        print(json.dumps(body.get("review"), indent=2)[:2000])
        print("Assistant message:", body.get("assistant_message"))

        # Find persisted assistant message in DB
        async with async_session_factory() as session:
            messages = await ChatMessageRepository.get_session_messages(session=session, session_id=uuid.UUID(session_id), profile_id=test_profile_id)
            found = None
            for m in messages:
                if str(m.id) == body.get("assistant_message", {}).get("id"):
                    found = m
                    break
            if found:
                print("Persisted assistant message found in DB:")
                print("id:", found.id)
                print("content (truncated 1000 chars):")
                print(found.content[:1000])
            else:
                print("Could not find persisted assistant message with id", body.get("assistant_message", {}).get("id"))

        # Verify original non-agentic endpoint still works
        print("Verifying non-agentic endpoint still functions")
        r3 = await client.post(f"/api/v1/chat/sessions/{session_id}/messages", json={"content": "A simple check: what is 2+2?"})
        print("Non-agentic status:", r3.status_code)
        if r3.status_code == 201:
            print("Non-agentic response:", r3.json())
        else:
            print("Non-agentic response body:", await r3.aread())

        # Cleanup
        print("Cleaning up: deleting test session")
        async with async_session_factory() as session:
            chat_session = await ChatSessionRepository.get_session_by_id(session=session, session_id=uuid.UUID(session_id), profile_id=test_profile_id)
            if chat_session:
                await ChatSessionRepository.delete_session(session=session, chat_session=chat_session)
                print("Deleted test session")


if __name__ == "__main__":
    asyncio.run(main())
