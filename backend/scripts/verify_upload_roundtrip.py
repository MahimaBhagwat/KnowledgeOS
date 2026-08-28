#!/usr/bin/env python3
import asyncio
import uuid
from pathlib import Path

from httpx import AsyncClient
from httpx._transports.asgi import ASGITransport

from app.main import app
from app.api.deps import get_current_user


async def main():
    owner_id = uuid.uuid4()
    owner_email = f"verify+{owner_id.hex[:8]}@example.com"

    async def _owner_user():
        return {"profile_id": str(owner_id), "email": owner_email, "user_metadata": {}}

    app.dependency_overrides[get_current_user] = _owner_user

    transport = ASGITransport(app=app)
    # prepare a small text file to upload
    file_bytes = b"Roundtrip upload test\n"

    # ensure a DB profile exists for owner (FolderService and ingestion expect a profiles row)
    from app.core.database import async_session_factory
    from app.users.services import UserService
    from app.users.schemas import ProfileCreate

    async with async_session_factory() as session:
        profile = await UserService.get_profile_by_id(session, owner_id)
        if profile is None:
            print("Registering profile row for owner")
            schema = ProfileCreate(id=owner_id, email=owner_email, name="Verify Upload", avatar_url=None)
            await UserService.register_profile(session, schema)

    async with AsyncClient(transport=transport, base_url="http://testserver", timeout=30) as client:
        # Ensure the user has a folder to upload into by creating a custom folder
        print("Creating folder for owner")
        r_folder = await client.post("/api/v1/folders/", json={"name": "verify-uploads"})
        print("Create folder status:", r_folder.status_code)
        folder_id = None
        if r_folder.status_code == 201:
            folder_id = r_folder.json().get("id")
            print("Created folder id:", folder_id)

        # POST multipart/form-data to upload
        files = {"file": ("roundtrip.txt", file_bytes, "text/plain")}
        data = {}
        if folder_id:
            data["folder_id"] = folder_id
        print("Uploading file for owner", owner_id)
        r = await client.post("/api/v1/documents/upload", files=files, data=data)
        print("Upload status:", r.status_code)
        try:
            print("Upload json:", r.json())
        except Exception:
            print("Upload raw:", await r.aread())
            return

        if r.status_code != 201:
            print("Upload failed")
            return

        doc = r.json()
        doc_id = doc.get("id")
        print("Created document id:", doc_id)

        # Now GET content
        print("Fetching content for document", doc_id)
        r2 = await client.get(f"/api/v1/documents/{doc_id}/content")
        print("Content status:", r2.status_code)
        if r2.status_code == 200:
            data = await r2.aread()
            print("Content bytes:", data.decode('utf-8'))
        else:
            print("Content body:", await r2.aread())


if __name__ == '__main__':
    asyncio.run(main())
