from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.chat.schemas import (
    ChatMessageCreate,
    ChatMessageOut,
    ChatSessionCreate,
    ChatSessionOut,
    ChatSessionUpdate,
)
from app.chat.services import ChatService

router: APIRouter = APIRouter(prefix="/chat", tags=["chat"])
service = ChatService()


@router.post("/sessions", response_model=ChatSessionOut, status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: ChatSessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> ChatSessionOut:
    profile_id = UUID(current_user["profile_id"])
    chat_session = await service.create_session(session=db, profile_id=profile_id, title=payload.title)
    return ChatSessionOut.from_orm(chat_session)


@router.get("/sessions", response_model=List[ChatSessionOut])
async def list_sessions(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> List[ChatSessionOut]:
    profile_id = UUID(current_user["profile_id"])
    sessions = await service.list_user_sessions(session=db, profile_id=profile_id, skip=skip, limit=limit)
    return [ChatSessionOut.from_orm(s) for s in sessions]


@router.get("/sessions/{session_id}", response_model=ChatSessionOut)
async def get_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> ChatSessionOut:
    profile_id = UUID(current_user["profile_id"])
    chat_session = await service.get_session(session=db, session_id=session_id, profile_id=profile_id)
    return ChatSessionOut.from_orm(chat_session)


@router.patch("/sessions/{session_id}", response_model=ChatSessionOut)
async def update_session(
    session_id: UUID,
    payload: ChatSessionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> ChatSessionOut:
    profile_id = UUID(current_user["profile_id"])
    updated = await service.update_session(session=db, session_id=session_id, update_data=payload, profile_id=profile_id)
    return ChatSessionOut.from_orm(updated)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> Response:
    profile_id = UUID(current_user["profile_id"])
    await service.delete_session(session=db, session_id=session_id, profile_id=profile_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/sessions/{session_id}/messages", response_model=ChatMessageOut, status_code=status.HTTP_201_CREATED)
async def post_message(
    session_id: UUID,
    payload: ChatMessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> ChatMessageOut:
    profile_id = UUID(current_user["profile_id"])
    assistant_message = await service.send_message(session=db, session_id=session_id, profile_id=profile_id, message_data=payload)
    return ChatMessageOut.model_validate(assistant_message)


@router.post("/sessions/{session_id}/messages/agentic", status_code=status.HTTP_201_CREATED)
async def post_message_agentic(
    session_id: UUID,
    payload: ChatMessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Run the Planner -> Executor -> Reviewer agentic pipeline and return the detailed result.

    The response is a JSON object with keys: plan, execution, review, assistant_message.
    """
    profile_id = UUID(current_user["profile_id"])
    result = await service.send_message_agentic(session=db, session_id=session_id, profile_id=profile_id, message_data=payload)
    return result


from fastapi.responses import StreamingResponse
import json


@router.post("/sessions/{session_id}/messages/stream", status_code=status.HTTP_200_OK)
async def post_message_stream(
    session_id: UUID,
    payload: ChatMessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Stream assistant tokens to the client as Server-Sent Events (SSE).

    Each token event is a line-delimited SSE 'data' payload containing JSON of the form:
      {"type": "token", "content": "..."}

    After the stream completes, a final 'done' event is emitted with the persisted
    assistant message metadata.
    """
    profile_id = UUID(current_user["profile_id"])

    async def generator():
        async for chunk in service.stream_message(session=db, session_id=session_id, profile_id=profile_id, message_data=payload):
            # service.stream_message already yields properly formatted SSE data lines
            yield chunk

    return StreamingResponse(generator(), media_type="text/event-stream")


__all__ = ["router"]