#!/usr/bin/env python3
import asyncio
from app.core.database import async_session_factory
from sqlalchemy import text

async def main():
    async with async_session_factory() as session:
        rows = await session.execute(text("SELECT id, profile_id, name, folder_type, is_system_folder FROM folders WHERE is_system_folder = true ORDER BY profile_id LIMIT 50"))
        allrows = rows.fetchall()
        print(f"Found {len(allrows)} system folder rows")
        for r in allrows:
            print(r)

if __name__ == '__main__':
    asyncio.run(main())
