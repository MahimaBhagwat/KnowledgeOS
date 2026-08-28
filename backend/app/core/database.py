from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeMeta, declarative_base

from app.core.config import settings


def _make_async_database_url(database_url: str) -> str:
    """Ensure the database URL is compatible with SQLAlchemy async engines.

    If the provided URL uses the postgres scheme without an async driver
    (postgresql://) it is converted to the asyncpg form
    (postgresql+asyncpg://). If the URL already contains an async driver
    or uses a different scheme, it is returned unchanged.
    """
    if database_url.startswith("postgresql+"):
        return database_url
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return database_url


# Compose the async database URL from settings (do not modify settings itself)
ASYNC_DATABASE_URL: str = _make_async_database_url(str(settings.database_url))


# Create the SQLAlchemy async engine. No database IO occurs at import time.
engine: AsyncEngine = create_async_engine(
    ASYNC_DATABASE_URL,
    future=True,
    echo=False,
    pool_pre_ping=True,
)


# Async session factory for application use
async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


# Declarative base for model definitions
Base: DeclarativeMeta = declarative_base()


__all__ = ["engine", "async_session_factory", "Base", "ASYNC_DATABASE_URL"]
