from __future__ import annotations

from typing import Any, AsyncGenerator, Dict, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.core.security import TokenError, decode_token
from app.users import schemas
from app.users.models import Profile
from app.users.services import UserService


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional scope around a series of operations.

    Yields an AsyncSession from the application's async_session_factory and
    ensures the session is closed once the request is finished.
    """
    async with async_session_factory() as session:
        yield session


# Reusable HTTP bearer scheme with auto_error=False so the dependency can
# return a consistent 401 response instead of the default 403 from HTTPBearer.
_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Validate the incoming bearer token and return a minimal user context.

    The dependency decodes the Supabase JWT, checks whether the profile row
    already exists, and bootstraps the profile plus default preferences/folders
    only when it is missing.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(credentials.credentials)
    except TokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        profile_id = UUID(subject)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    profile = await db.get(Profile, profile_id)
    if profile is None:
        email = payload.get("email")
        if not isinstance(email, str) or not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to bootstrap profile without an email claim",
                headers={"WWW-Authenticate": "Bearer"},
            )

        raw_metadata = payload.get("user_metadata")
        user_metadata = raw_metadata if isinstance(raw_metadata, dict) else {}

        name = user_metadata.get("full_name")
        if not isinstance(name, str) or not name.strip():
            name = user_metadata.get("name")
        if not isinstance(name, str) or not name.strip():
            name = None

        avatar_url = user_metadata.get("avatar_url")
        if not isinstance(avatar_url, str) or not avatar_url.strip():
            avatar_url = None

        profile_schema = schemas.ProfileCreate(
            id=profile_id,
            email=email,
            name=name,
            avatar_url=avatar_url,
        )
        await UserService.register_profile(db, profile_schema)

    return {
        "profile_id": str(profile_id),
        "email": payload.get("email") or f"{subject}@supabase.user",
        "user_metadata": payload.get("user_metadata", {}),
    }
