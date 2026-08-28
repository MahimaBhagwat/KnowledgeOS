#!/usr/bin/env python3
import asyncio
from httpx import AsyncClient
from httpx._transports.asgi import ASGITransport
from app.main import app
from app.api.deps import get_current_user
from app.core.database import async_session_factory

async def main():
    # pick an existing profile id from the DB
    async with async_session_factory() as session:
        from sqlalchemy import text
        row = await session.execute(text("SELECT id, email FROM profiles LIMIT 1"))
        first = row.first()
        if first is None:
            print("No profiles in DB to test; create one and rerun")
            return
        profile_id, email = first
        print("Using profile:", profile_id, email)

        # inspect folders in DB for this profile
        rows = await session.execute(text("SELECT id, name, folder_type, is_system_folder, created_at FROM folders WHERE profile_id = :pid ORDER BY name"), {"pid": str(profile_id)})
        print("DB folders rows:")
        for r in rows.fetchall():
            print(r)

    async def _user():
        return {"profile_id": str(profile_id), "email": email, "user_metadata": {}}

    app.dependency_overrides[get_current_user] = _user
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        r = await client.get('/api/v1/folders/')
        print('Status:', r.status_code)
        try:
            print('JSON response:')
            print(r.json())
        except Exception:
            print('Raw body:', (await r.aread()).decode('utf-8', errors='replace'))

if __name__ == '__main__':
    asyncio.run(main())
