#!/usr/bin/env python3
import asyncio
from uuid import UUID
from app.core.database import async_session_factory
from app.folders.repositories import FolderRepository

async def main():
    # Use an example existing profile_id observed earlier in the DB list
    profile_id = UUID('07f04bdc-dbe0-4890-82cb-a3c78567ff89')
    async with async_session_factory() as session:
        folders = await FolderRepository.get_user_folders(session, profile_id)
        print(f"Folders for profile {profile_id} (")
        for f in folders:
            print(f"- {f.name} ({getattr(f,'folder_type', None)}) system={f.is_system_folder}")

if __name__ == '__main__':
    asyncio.run(main())
