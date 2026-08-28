from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.insights.schemas import DocumentInsightsResponse, FolderInsightsResponse
from app.insights.services import InsightService

router: APIRouter = APIRouter(prefix="/insights", tags=["insights"])
service = InsightService()


@router.post("/documents/{document_id}", response_model=DocumentInsightsResponse)
async def generate_document_insights(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> DocumentInsightsResponse:
    profile_id = UUID(current_user["profile_id"])
    payload = await service.generate_document_insights(session=db, profile_id=profile_id, document_id=document_id)
    return DocumentInsightsResponse.model_validate(payload)


@router.post("/folders/{folder_id}", response_model=FolderInsightsResponse)
async def generate_folder_insights(
    folder_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> FolderInsightsResponse:
    profile_id = UUID(current_user["profile_id"])
    payload = await service.generate_folder_insights(session=db, profile_id=profile_id, folder_id=folder_id)
    return FolderInsightsResponse.model_validate(payload)


__all__ = ["router"]
