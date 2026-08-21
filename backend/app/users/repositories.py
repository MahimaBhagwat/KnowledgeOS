from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.users.models import Profile, UserPreference


class ProfileRepository:
    """Repository for Profile CRUD operations.

    All methods accept an AsyncSession instance. No session is created inside
    the repository to keep transaction scoping under caller control.
    """

    @staticmethod
    async def create(session: AsyncSession, *, data: Dict[str, Any], commit: bool = True) -> Profile:
        """Create a new Profile from the provided data dict and return it.

        Args:
            session: Active AsyncSession provided by dependency injection.
            data: Mapping of Profile fields (email, name, avatar_url, etc.).
            commit: Whether to commit the transaction inside this method. When
                    False, the caller is responsible for committing the session.
        Returns:
            The newly created Profile instance.
        """
        profile = Profile(**data)
        session.add(profile)
        if commit:
            await session.commit()
            await session.refresh(profile)
        else:
            # If not committing here, refresh may not be necessary; return the instance
            # The caller can refresh after a later commit if desired.
            pass
        return profile

    @staticmethod
    async def get_by_id(session: AsyncSession, profile_id: UUID) -> Optional[Profile]:
        stmt = select(Profile).where(Profile.id == profile_id)
        result = await session.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def get_by_email(session: AsyncSession, email: str) -> Optional[Profile]:
        stmt = select(Profile).where(Profile.email == email)
        result = await session.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def update(session: AsyncSession, profile: Profile, *, updates: Dict[str, Any], commit: bool = True) -> Profile:
        """Apply updates to the provided Profile instance and persist changes.

        The caller is responsible for retrieving the Profile instance (e.g. via
        get_by_id) and passing it here. The repository will set attributes,
        and optionally commit the transaction and refresh the instance.
        """
        for key, value in updates.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        session.add(profile)
        if commit:
            await session.commit()
            await session.refresh(profile)
        return profile

    @staticmethod
    async def delete(session: AsyncSession, profile: Profile, commit: bool = True) -> None:
        """Remove the given Profile from the database.

        Note: cascade rules defined on the ORM model will ensure related
        user preferences are deleted as configured.
        """
        await session.delete(profile)
        if commit:
            await session.commit()


class UserPreferenceRepository:
    """Repository for UserPreference CRUD operations."""

    @staticmethod
    async def create(session: AsyncSession, *, data: Dict[str, Any], commit: bool = True) -> UserPreference:
        preference = UserPreference(**data)
        session.add(preference)
        if commit:
            await session.commit()
            await session.refresh(preference)
        return preference

    @staticmethod
    async def get_by_id(session: AsyncSession, preference_id: UUID) -> Optional[UserPreference]:
        stmt = select(UserPreference).where(UserPreference.id == preference_id)
        result = await session.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def get_by_profile_id(session: AsyncSession, profile_id: UUID) -> Optional[UserPreference]:
        stmt = select(UserPreference).where(UserPreference.profile_id == profile_id)
        result = await session.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def update(session: AsyncSession, preference: UserPreference, *, updates: Dict[str, Any], commit: bool = True) -> UserPreference:
        for key, value in updates.items():
            if hasattr(preference, key):
                setattr(preference, key, value)
        session.add(preference)
        if commit:
            await session.commit()
            await session.refresh(preference)
        return preference

    @staticmethod
    async def delete(session: AsyncSession, preference: UserPreference, commit: bool = True) -> None:
        await session.delete(preference)
        if commit:
            await session.commit()


__all__ = [
    "ProfileRepository",
    "UserPreferenceRepository",
]
