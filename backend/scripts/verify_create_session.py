#!/usr/bin/env python3
import asyncio
import uuid
import json
from httpx import AsyncClient
from httpx._transports.asgi import ASGITransport
from datetime import datetime

from app.main import app
from app.api.deps import get_current_user
from app.core.database import async_session_factory
from app.users.services import UserService
from app.users.schemas import ProfileCreate


async def ensure_profile(profile_id: uuid.UUID, email: str):
    async with async_session_factory() as session:
        profile = await UserService.get_profile_by_id(session, profile_id)
        if profile is None:
            schema = ProfileCreate(id=profile_id, email=email, name="Verify Create", avatar_url=None)
            await UserService.register_profile(session, schema)


async def main():
    test_profile_id = uuid.uuid4()
    test_email = f"verify+{test_profile_id.hex[:8]}@example.com"
    await ensure_profile(test_profile_id, test_email)

    async def _fake_current_user():
        return {"profile_id": str(test_profile_id), "email": test_email, "user_metadata": {}}

    app.dependency_overrides[get_current_user] = _fake_current_user
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver", timeout=30) as client:
        print("POST /api/v1/chat/sessions with empty JSON {} (no title field)")
        r = await client.post('/api/v1/chat/sessions', json={})
        print('Status code:', r.status_code)
        try:
            print('Body:', json.dumps(r.json(), indent=2))
        except Exception:
            print('Raw body:', (await r.aread()).decode('utf-8', errors='replace'))


if __name__ == '__main__':
    asyncio.run(main())
