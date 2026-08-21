from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.chat.models import ChatMessage, ChatSession
from app.chat.schemas import ChatSessionUpdate


class ChatSessionRepository:
    """Repository for ChatSession persistence operations.

    All methods enforce tenant isolation via profile_id filtering.
    """

    @staticmethod
    async def create_session(session: AsyncSession, profile_id: UUID, title: str = "New Chat") -> ChatSession:
        """Create and persist a new ChatSession for the given profile_id."""
        chat_session = ChatSession(profile_id=profile_id, title=title)
        session.add(chat_session)
        await session.flush()
        new_session_id = chat_session.id  
        await session.commit()

        stmt = (
            select(ChatSession)
            .where(ChatSession.id == new_session_id)
            .options(selectinload(ChatSession.messages))
        )
        result = await session.execute(stmt)
        return result.scalar_one()

    @staticmethod
    async def get_session_by_id(session: AsyncSession, session_id: UUID, profile_id: UUID) -> Optional[ChatSession]:
        """Retrieve a ChatSession by id scoped to profile_id. Returns None if not found/unauthorized."""
        stmt = (
            select(ChatSession)
            .where(ChatSession.id == session_id, ChatSession.profile_id == profile_id)
            .options(selectinload(ChatSession.messages))
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_sessions(session: AsyncSession, profile_id: UUID, skip: int = 0, limit: int = 50) -> List[ChatSession]:
        """Retrieve paginated chat sessions for a user ordered by updated_at desc."""
        stmt = (
            select(ChatSession)
            .where(ChatSession.profile_id == profile_id)
            .order_by(ChatSession.updated_at.desc())
            .offset(skip)
            .limit(limit)
            .options(selectinload(ChatSession.messages))
        )
        result = await session.execute(stmt)
        return result.scalars().all()


    @staticmethod
    async def update_session(session: AsyncSession, chat_session: ChatSession, update_data: ChatSessionUpdate) -> ChatSession:
        """Apply updates from a ChatSessionUpdate onto the provided ChatSession entity and persist changes."""
        update_payload = {}
        if hasattr(update_data, "model_dump"):
            update_payload = update_data.model_dump(exclude_unset=True)
        else:
            update_payload = getattr(update_data, "dict")(exclude_unset=True)

        for key, value in update_payload.items():
            setattr(chat_session, key, value)

        session.add(chat_session)
        session_id = chat_session.id  
        await session.commit()

        stmt = (
            select(ChatSession)
            .where(ChatSession.id == session_id)
            .options(selectinload(ChatSession.messages))
        )
        result = await session.execute(stmt)
        return result.scalar_one()


    @staticmethod
    async def delete_session(session: AsyncSession, chat_session: ChatSession) -> None:
        """Delete a ChatSession (cascades to messages at DB/ORM level)."""
        await session.delete(chat_session)
        await session.commit()


class ChatMessageRepository:
    """Repository for ChatMessage persistence operations.

    All methods strictly enforce profile_id tenant isolation.
    """

    @staticmethod
    async def create_message(
        session: AsyncSession,
        session_id: UUID,
        profile_id: UUID,
        role: str,
        content: str,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        citations: Optional[List[dict]] = None,
    ) -> ChatMessage:
        """Create and persist a chat message linked to a session and profile."""
        message = ChatMessage(
            session_id=session_id,
            profile_id=profile_id,
            role=role,
            content=content,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            citations=citations,
        )
        session.add(message)
        await session.commit()
        await session.refresh(message)
        return message

    @staticmethod
    async def get_session_messages(
        session: AsyncSession, session_id: UUID, profile_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[ChatMessage]:
        """Retrieve messages for a session ordered by created_at ascending, scoped to profile_id."""
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id, ChatMessage.profile_id == profile_id)
            .order_by(ChatMessage.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await session.execute(stmt)
        return result.scalars().all()
