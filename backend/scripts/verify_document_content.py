#!/usr/bin/env python3
import asyncio
import uuid
import json
from pathlib import Path
from datetime import datetime

from httpx import AsyncClient
from sqlalchemy import text
from httpx._transports.asgi import ASGITransport

from app.main import app
from app.api.deps import get_current_user
from app.core.database import async_session_factory
from app.users.services import UserService
from app.users.schemas import ProfileCreate
from app.documents.services import DocumentService
from app.documents import schemas


async def ensure_profile(profile_id: uuid.UUID, email: str):
    async with async_session_factory() as session:
        profile = await UserService.get_profile_by_id(session, profile_id)
        if profile is None:
            schema = ProfileCreate(id=profile_id, email=email, name="Verify Doc", avatar_url=None)
            await UserService.register_profile(session, schema)


async def main():
    # create owner profile
    owner_id = uuid.uuid4()
    owner_email = f"verify+{owner_id.hex[:8]}@example.com"
    await ensure_profile(owner_id, owner_email)

    # create other profile
    other_id = uuid.uuid4()
    other_email = f"verify+{other_id.hex[:8]}@example.com"
    await ensure_profile(other_id, other_email)

    print("owner_id=", owner_id)
    print("other_id=", other_id)

    # override dependency with owner
    async def _owner_user():
        return {"profile_id": str(owner_id), "email": owner_email, "user_metadata": {}}

    app.dependency_overrides[get_current_user] = _owner_user

    transport = ASGITransport(app=app)

    # create a physical file on disk under uploads/{owner_id}/testfile.txt
    # Create the file where the running app expects it: backend/uploads/{owner_id}
    base = Path.cwd() / "uploads" / str(owner_id)
    base.mkdir(parents=True, exist_ok=True)
    test_path = base / "testfile.txt"
    test_content = "Hello from owner\n"
    test_path.write_text(test_content, encoding="utf-8")

    async with AsyncClient(transport=transport, base_url="http://testserver", timeout=30) as client:
        # create a Document DB record directly via DocumentService.create_document
        # Need folder_id: use user's uploaded folder
        async with async_session_factory() as session:
            uploaded_folder = await session.execute(
                            text("SELECT id FROM folders WHERE profile_id=:pid AND folder_type='uploaded' LIMIT 1"),
                {"pid": str(owner_id)},
            )
            row = uploaded_folder.first()
            if row is None:
                # rely on service to auto-create if missing by passing None
                folder_id = None
            else:
                folder_id = row[0]

        doc_create = schemas.DocumentCreate(
            name="testfile",
            file_type=schemas.DocumentTypeEnum.TXT,
            file_size=test_path.stat().st_size,
            is_favorite=False,
            folder_id=folder_id,
            file_path=f"uploads/{owner_id}/testfile.txt",
        )

        # create via service
        async with async_session_factory() as session:
            document = await DocumentService.create_document(session, doc_create, owner_id)
            doc_id = str(document.id)
            print("Created document id:", doc_id)

        # inspect DB for the created document
        async with async_session_factory() as session:
                    res = await session.execute(text("SELECT id, profile_id, file_path, is_deleted FROM documents WHERE id=:id"), {"id": doc_id})
                    print("DB document row:", res.first())

        # fetch document metadata as owner (sanity check)
        print("Requesting metadata as owner")
        # inspect candidate upload paths for debugging
        candidate1 = Path.cwd() / "uploads" / str(owner_id) / "testfile.txt"
        candidate2 = Path.cwd().parent / "uploads" / str(owner_id) / "testfile.txt"
        print("Candidate backend/uploads exists:", candidate1.exists(), candidate1)
        print("Candidate repo_root/uploads exists:", candidate2.exists(), candidate2)

        # replicate router's resolution logic for both possible base dirs
        raw_path = Path(f"uploads/{owner_id}/testfile.txt")
        for base_dir in [Path.cwd() / "uploads", Path.cwd().parent / "uploads"]:
            try:
                try:
                    rel = raw_path.relative_to("uploads")
                except Exception:
                    rel = raw_path
                resolved = (base_dir / rel).resolve()
                ok = True
                try:
                    resolved.relative_to(base_dir.resolve())
                    rel_ok = True
                except Exception:
                    rel_ok = False
                print(f"Base {base_dir} -> resolved {resolved} exists={resolved.exists()} rel_ok={rel_ok}")
            except Exception as exc:
                print("Resolution error for base", base_dir, exc)
        r_meta = await client.get(f"/api/v1/documents/{doc_id}")
        print("Metadata status:", r_meta.status_code)
        try:
            print("Metadata json:", r_meta.json())
        except Exception:
            print("Metadata raw:", (await r_meta.aread()))

        # fetch as owner
        print("Requesting content as owner")
        r = await client.get(f"/api/v1/documents/{doc_id}/content")
        print("Owner status:", r.status_code)
        if r.status_code == 200:
                    body_text = (await r.aread()).decode("utf-8")
                    print("Owner received bytes:\n", body_text)
        else:
                    print("Owner error body:", await r.aread())

        # now override dependency to other user
        async def _other_user():
            return {"profile_id": str(other_id), "email": other_email, "user_metadata": {}}

        app.dependency_overrides[get_current_user] = _other_user

        print("Requesting content as other user (should be 404)")
        r2 = await client.get(f"/api/v1/documents/{doc_id}/content")
        print("Other status:", r2.status_code)
        try:
            print("Other body:", r2.json())
        except Exception:
            print("Other raw body:", (await r2.aread()).decode('utf-8', errors='replace'))

        # cleanup file and DB entry
        print("Cleaning up: removing file")
        try:
            test_path.unlink()
        except Exception:
            pass


if __name__ == '__main__':
    asyncio.run(main())
