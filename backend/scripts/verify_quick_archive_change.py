#!/usr/bin/env python3
import asyncio
import json
import uuid

from httpx import AsyncClient
from httpx._transports.asgi import ASGITransport

from app.main import app
from app.api.deps import get_current_user
from app.core.database import async_session_factory
from app.users.services import UserService
from app.users.schemas import ProfileCreate
from app.folders.repositories import FolderRepository
from app.notes.repositories import NoteRepository


async def ensure_profile(profile_id: uuid.UUID, email: str):
    async with async_session_factory() as session:
        profile = await UserService.get_profile_by_id(session, profile_id)
        if profile is None:
            print(f"Creating profile {profile_id} {email}")
            schema = ProfileCreate(id=profile_id, email=email, name="Verify QuickArchive", avatar_url=None)
            await UserService.register_profile(session, schema)
            print("Profile created")
        else:
            print(f"Profile {profile_id} already exists")


async def main():
    test_profile_id = uuid.uuid4()
    test_email = f"verify+{test_profile_id.hex[:8]}@example.com"

    await ensure_profile(test_profile_id, test_email)

    # Override dependency
    async def _fake_current_user():
        return {"profile_id": str(test_profile_id), "email": test_email, "user_metadata": {}}

    app.dependency_overrides[get_current_user] = _fake_current_user

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver", timeout=60) as client:
        # GET folders (use trailing slash to avoid a 307 redirect)
        r = await client.get("/api/v1/folders/")
        print("GET /folders status:", r.status_code)
        try:
            folders = r.json()
        except Exception:
            text = await r.aread()
            print("Failed to parse /folders response body:", text)
            return
        print("Folders returned for new profile:")
        print(json.dumps(folders, indent=2))

        sys_folders = [f for f in folders if f.get("is_system_folder")]
        print("System folders count:", len(sys_folders))
        print("System folder names:", [f.get("folder_type") for f in sys_folders])

        # Create a note with no folder_id
        payload = {"title": "Test Note", "content": "This is a quick test note."}
        r2 = await client.post("/api/v1/notes/", json=payload)
        print("POST /notes status:", r2.status_code)
        if r2.status_code == 201:
            note = r2.json()
            print("Created note:", json.dumps(note, indent=2))
            print("Stored folder_id:", note.get("folder_id"))
        else:
            print("Create note failed:", await r2.aread())

        # Check an existing profile for pre-existing Quick Notes / Archive (pick one known profile if available)
        # We will inspect the DB for an existing profile that has system folders for demonstration.
        async with async_session_factory() as session:
            # Find any profile that has system folders besides 'uploaded'
            rows = await FolderRepository.get_user_folders(session, test_profile_id)
            # This was for the new profile; to check an existing profile we will fetch first profile found in DB
            pass


if __name__ == "__main__":
    asyncio.run(main())
