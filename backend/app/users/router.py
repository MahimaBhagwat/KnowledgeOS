from __future__ import annotations

from typing import Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.users import schemas
from app.users.services import UserService
from app.core.logging import get_logger

logger = get_logger(__name__)

router: APIRouter = APIRouter(prefix="/users", tags=["users"])


@router.get("/profile", response_model=schemas.ProfileOut)
async def get_profile(
    db: AsyncSession = Depends(get_db), current_user: Dict[str, str] = Depends(get_current_user)
) -> schemas.ProfileOut:
    raw_id = current_user.get("profile_id")
    profile_id = UUID(raw_id) if isinstance(raw_id, str) else raw_id

    profile = await UserService.get_profile_by_id(db, profile_id)

    if profile is None:
        logger.info(f"Creating new profile for profile_id: {profile_id}")
        email = current_user.get("email") or f"{profile_id}@supabase.user"
        metadata = current_user.get("user_metadata") or {}
        name = metadata.get("full_name") or email.split("@")[0]
        
        # Use ProfileCreate schema and register_profile method
        create_schema = schemas.ProfileCreate(
            id=profile_id,
            email=email,
            name=name
        )

        profile = await UserService.register_profile(
            db, 
            create_schema
        )
        
        # raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return schemas.ProfileOut.model_validate(profile)


@router.patch("/profile", response_model=schemas.ProfileOut)
async def patch_profile(
    patch: schemas.ProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, str] = Depends(get_current_user),
) -> schemas.ProfileOut:
    profile_id = current_user.get("profile_id")
    profile = await UserService.get_profile_by_id(db, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    updates = patch.model_dump(exclude_none=True)
    updated = await UserService.update_profile(db, profile, updates)
    return schemas.ProfileOut.model_validate(updated)


@router.get("/preferences", response_model=schemas.UserPreferenceOut)
async def get_preferences(
    db: AsyncSession = Depends(get_db), current_user: Dict[str, str] = Depends(get_current_user)
) -> schemas.UserPreferenceOut:
    profile_id = current_user.get("profile_id")
    pref = await UserService.get_preferences_for_profile(db, profile_id)
    if pref is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preferences not found")
    return schemas.UserPreferenceOut.model_validate(pref)


@router.patch("/preferences", response_model=schemas.UserPreferenceOut)
async def patch_preferences(
    patch: schemas.UserPreferenceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, str] = Depends(get_current_user),
) -> schemas.UserPreferenceOut:
    profile_id = current_user.get("profile_id")
    pref = await UserService.get_preferences_for_profile(db, profile_id)
    if pref is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preferences not found")

    updates = patch.model_dump(exclude_none=True)
    updated = await UserService.update_preferences(db, pref, updates)
    return schemas.UserPreferenceOut.model_validate(updated)
