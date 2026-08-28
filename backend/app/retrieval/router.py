from __future__ import annotations

from typing import Dict
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.embeddings import generate_query_embedding
from app.retrieval.retriever import SemanticRetriever
from app.retrieval.schemas import SearchQueryRequest, SearchQueryResponse

router: APIRouter = APIRouter(prefix="/retrieval", tags=["retrieval"])


@router.post("/", response_model=SearchQueryResponse)
async def search_query(
    payload: SearchQueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, str] = Depends(get_current_user),
) -> SearchQueryResponse:
    profile_id = UUID(current_user["profile_id"])
    query_embedding = generate_query_embedding(payload.query)

    retriever = SemanticRetriever()
    contexts = await retriever.retrieve_relevant_chunks(
        session=db,
        query_embedding=query_embedding,
        profile_id=profile_id,
        folder_id=payload.folder_id,
        top_k=payload.top_k,
        score_threshold=payload.score_threshold,
    )
    formatted_context = retriever.format_context_for_llm(contexts)
    return SearchQueryResponse(
        contexts=contexts,
        formatted_prompt_context=formatted_context,
    )


__all__ = ["router"]
