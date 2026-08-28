from __future__ import annotations

from typing import Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.folders.services import FolderService
from app.users.repositories import ProfileRepository, UserPreferenceRepository
from app.users import schemas
from app.users.models import Profile, UserPreference


class UserService:
    """Orchestrates user-related business logic.

    This service sits above the repository layer and implements multi-step
    workflows that must run atomically within the same database transaction.
    """

    @staticmethod
    async def register_profile(session: AsyncSession, schema: schemas.ProfileCreate) -> Profile:
        """Register a new profile, seed preferences, and create system folders atomically.

        Steps:
        1. Create a Profile record (without committing)
        2. Create a matching UserPreference record (without committing)
        3. Create default system folders (without committing)
        4. Commit once to ensure everything is persisted atomically

        Raises:
            IntegrityError when unique constraints (e.g., email) are violated.
        """
        try:
            # Create profile instance without committing; repository returns the instance
            profile = await ProfileRepository.create(session, data=schema.model_dump(), commit=False)

            # Seed default preferences linked to the new profile
            pref_data: Dict[str, object] = {
                "profile_id": profile.id,
                "theme": "light",
                "streaming_enabled": False,
                "planner_enabled": True,
                "reviewer_enabled": True,
            }
            _ = await UserPreferenceRepository.create(session, data=pref_data, commit=False)

            _ = await FolderService.create_default_system_folders(session, profile.id, commit=False)

            # Commit once to persist both records atomically
            await session.commit()

            # Refresh profile to ensure it has DB defaults and relationships populated
            await session.refresh(profile)
            return profile
        except IntegrityError:
            await session.rollback()
            raise

    @staticmethod
    async def get_profile_by_id(session: AsyncSession, profile_id) -> Optional[Profile]:
        return await ProfileRepository.get_by_id(session, profile_id)

    @staticmethod
    async def get_profile_by_email(session: AsyncSession, email: str) -> Optional[Profile]:
        return await ProfileRepository.get_by_email(session, email)

    @staticmethod
    async def update_profile(session: AsyncSession, profile: Profile, updates: Dict[str, object]) -> Profile:
        return await ProfileRepository.update(session, profile, updates=updates, commit=True)

    @staticmethod
    async def delete_profile(session: AsyncSession, profile: Profile) -> None:
        await ProfileRepository.delete(session, profile, commit=True)

    @staticmethod
    async def get_preferences_for_profile(session: AsyncSession, profile_id) -> Optional[UserPreference]:
        return await UserPreferenceRepository.get_by_profile_id(session, profile_id)

    @staticmethod
    async def update_preferences(session: AsyncSession, preference: UserPreference, updates: Dict[str, object]) -> UserPreference:
        return await UserPreferenceRepository.update(session, preference, updates=updates, commit=True)


__all__ = ["UserService"]
