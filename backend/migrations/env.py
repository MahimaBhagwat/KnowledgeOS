"""Alembic env.py for asynchronous migrations.

This file is intentionally written to run migrations in async mode using
SQLAlchemy's AsyncEngine. It sources the async database URL from
app.core.database.ASYNC_DATABASE_URL which in turn derives from the
centralized Pydantic settings (app.core.config.settings).
Do not hardcode credentials here; the underlying settings read from the
environment (DATABASE_URL) or .env when appropriate.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
from logging.config import fileConfig
from typing import Optional

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

# Import application metadata and async URL derived from centralized settings
from app.core.database import ASYNC_DATABASE_URL, Base

# Import models so they are registered on Base.metadata for autogenerate
# Use guarded imports to allow alembic to run even if some feature modules
# are not yet implemented in incremental development phases.
try:
    import app.users.models as _users_models  # noqa: F401
except Exception:
    _users_models = None

try:
    import app.folders.models as _folders_models  # noqa: F401
except Exception:
    _folders_models = None

try:
    import app.documents.models as _documents_models  # noqa: F401
except Exception:
    _documents_models = None

try:
    import app.ingestion.models as _ingestion_models  # noqa: F401
except Exception:
    _ingestion_models = None

try:
    import app.chat.models as _chat_models  # noqa: F401
except Exception:
    _chat_models = None

# notes and insights models may not exist yet; guard their imports
try:
    import app.notes.models as _notes_models  # noqa: F401
except Exception:
    _notes_models = None

try:
    import app.insights.models as _insights_models  # noqa: F401
except Exception:
    _insights_models = None

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
logger = logging.getLogger("alembic.env")

# Provide the target metadata for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine, though
    an Engine is acceptable here as well. By skipping the Engine creation we
    avoid establishing a DB connection when generating SQL scripts.
    """
    url = ASYNC_DATABASE_URL
    if url.startswith("postgresql+asyncpg://"):
        # Alembic expects a sync dialect URL in offline mode; translate back
        url = url.replace("postgresql+asyncpg://", "postgresql://", 1)

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations using the provided connection (sync callback executed
    inside an async connection via run_sync).
    """
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode using an AsyncEngine and an async
    connection. The actual migration execution is performed synchronously
    inside connection.run_sync(do_run_migrations).
    """
    connectable: AsyncEngine = create_async_engine(
        ASYNC_DATABASE_URL,
        poolclass=pool.NullPool,
        future=True,
    )

    try:
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
    finally:
        await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
