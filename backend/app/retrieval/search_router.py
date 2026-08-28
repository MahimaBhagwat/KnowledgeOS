from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.retrieval.schemas import SearchRequest, SearchResponse
from app.retrieval.search_service import HybridSearchService

router: APIRouter = APIRouter(prefix="/search", tags=["search"])
search_service = HybridSearchService()


@router.post("/", response_model=SearchResponse)
async def search_post(
    payload: SearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> SearchResponse:
    """Perform hybrid search (vector cosine similarity + full-text keyword matching)
    across both Documents and Notes with Reciprocal Rank Fusion (RRF).
    """
    profile_id = UUID(current_user["profile_id"])
    return await search_service.search(
        session=db,
        profile_id=profile_id,
        request=payload,
    )


@router.get("/", response_model=SearchResponse)
async def search_get(
    q: str = Query(..., min_length=1, description="Search query string"),
    folder_id: Optional[UUID] = Query(None, description="Optional folder filter"),
    top_k: int = Query(10, ge=1, le=50, description="Max results to return"),
    source_type: Optional[str] = Query("all", description="'all', 'document', or 'note'"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> SearchResponse:
    """Perform hybrid search via GET query parameters."""
    profile_id = UUID(current_user["profile_id"])
    payload = SearchRequest(
        query=q,
        folder_id=folder_id,
        top_k=top_k,
        source_type=source_type,
    )
    return await search_service.search(
        session=db,
        profile_id=profile_id,
        request=payload,
    )


__all__ = ["router"]
