from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import ChatMessage, ChatSession
from app.chat.repositories import ChatMessageRepository, ChatSessionRepository
from app.chat.schemas import ChatMessageCreate, ChatSessionUpdate
from app.core.config import settings
from app.core.embeddings import generate_query_embedding
from app.notes.retriever import NoteRetriever, NoteRetrieverContext
from app.retrieval.retriever import RetrieverContext, SemanticRetriever


class ChatService:
    """Business logic for managing chat sessions and messages, including RAG orchestration.

    Also exposes an optional agentic pipeline (planner -> executor -> reviewer)
    implemented using the app.agents module and the project's litellm and
    retrieval components.
    """

    def __init__(
        self,
        retriever: Optional[SemanticRetriever] = None,
        note_retriever: Optional[NoteRetriever] = None,
    ) -> None:
        self._retriever = retriever or SemanticRetriever()
        self._note_retriever = note_retriever or NoteRetriever()

    async def _retrieve_composed_context(
        self,
        session: AsyncSession,
        query_text: str,
        profile_id: UUID,
        folder_id: Optional[UUID] = None,
        top_k: int = 5,
    ) -> tuple[str, Optional[List[Dict[str, Any]]]]:
        """Retrieve both document chunks and note chunks, build sectioned prompt context and unified citations."""
        try:
            query_embedding = generate_query_embedding(query_text)
        except Exception:
            query_embedding = []

        doc_contexts: List[RetrieverContext] = []
        note_contexts: List[NoteRetrieverContext] = []

        if query_embedding:
            try:
                doc_contexts = await self._retriever.retrieve_relevant_chunks(
                    session=session,
                    query_embedding=query_embedding,
                    profile_id=profile_id,
                    folder_id=folder_id,
                    top_k=top_k,
                )
            except Exception:
                doc_contexts = []

            try:
                note_contexts = await self._note_retriever.retrieve_relevant_chunks(
                    session=session,
                    query_embedding=query_embedding,
                    profile_id=profile_id,
                    folder_id=folder_id,
                    top_k=top_k,
                )
            except Exception:
                note_contexts = []

        doc_formatted = self._retriever.format_context_for_llm(doc_contexts)
        note_formatted = self._note_retriever.format_context_for_llm(note_contexts)

        sections: List[str] = []
        if doc_formatted:
            sections.append(f"--- Document Knowledge ---\n{doc_formatted}")
        if note_formatted:
            sections.append(f"--- User Notes ---\n{note_formatted}")

        system_context = "\n\n".join(sections).strip()

        citations: List[Dict[str, Any]] = []
        for ctx in doc_contexts:
            citations.append({
                "chunk_id": str(ctx.chunk_id),
                "document_id": str(ctx.document_id),
                "source_type": "document",
                "chunk_index": int(ctx.chunk_index),
                "similarity_score": float(ctx.similarity_score),
                "chunk_text": ctx.chunk_text,
            })

        for n_ctx in note_contexts:
            citations.append({
                "chunk_id": str(n_ctx.chunk_id),
                "document_id": str(n_ctx.note_id),  # Populated for frontend backward compatibility
                "note_id": str(n_ctx.note_id),
                "source_type": "note",
                "chunk_index": int(n_ctx.chunk_index),
                "similarity_score": float(n_ctx.similarity_score),
                "chunk_text": n_ctx.chunk_text,
            })

        citations_payload = None
        if citations:
            citations.sort(key=lambda x: x["similarity_score"], reverse=True)
            citations_payload = citations

        return system_context, citations_payload

    async def create_session(
        self,
        session: AsyncSession,
        profile_id: UUID,
        title: Optional[str] = None,
    ) -> ChatSession:
        title_value = title or "New Chat"
        return await ChatSessionRepository.create_session(session=session, profile_id=profile_id, title=title_value)

    async def get_session(self, session: AsyncSession, session_id: UUID, profile_id: UUID) -> ChatSession:
        chat_session = await ChatSessionRepository.get_session_by_id(session=session, session_id=session_id, profile_id=profile_id)
        if chat_session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")
        return chat_session

    async def list_user_sessions(self, session: AsyncSession, profile_id: UUID, skip: int = 0, limit: int = 50) -> List[ChatSession]:
        return await ChatSessionRepository.get_user_sessions(session=session, profile_id=profile_id, skip=skip, limit=limit)

    async def update_session(
        self,
        session: AsyncSession,
        session_id: UUID,
        update_data: ChatSessionUpdate,
        profile_id: UUID,
    ) -> ChatSession:
        chat_session = await ChatSessionRepository.get_session_by_id(session=session, session_id=session_id, profile_id=profile_id)
        if chat_session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")
        return await ChatSessionRepository.update_session(session=session, chat_session=chat_session, update_data=update_data)

    async def delete_session(self, session: AsyncSession, session_id: UUID, profile_id: UUID) -> None:
        chat_session = await ChatSessionRepository.get_session_by_id(session=session, session_id=session_id, profile_id=profile_id)
        if chat_session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")
        await ChatSessionRepository.delete_session(session=session, chat_session=chat_session)

    async def send_message(
        self,
        session: AsyncSession,
        session_id: UUID,
        profile_id: UUID,
        message_data: ChatMessageCreate,
    ) -> ChatMessage:
        """Handle incoming user message, perform retrieval, call LLM, and persist assistant reply."""
        chat_session = await ChatSessionRepository.get_session_by_id(session=session, session_id=session_id, profile_id=profile_id)
        if chat_session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")

        await ChatMessageRepository.create_message(
            session=session,
            session_id=session_id,
            profile_id=profile_id,
            role="user",
            content=message_data.content,
        )

        system_context, citations_payload = await self._retrieve_composed_context(
            session=session,
            query_text=message_data.content,
            profile_id=profile_id,
            folder_id=message_data.folder_id,
            top_k=message_data.top_k or 5,
        )

        try:
            all_messages = await ChatMessageRepository.get_session_messages(
                session=session,
                session_id=session_id,
                profile_id=profile_id,
                skip=0,
                limit=100,
            )
            recent_history = self._trim_history_by_token_budget(all_messages, max_tokens=2000)
        except Exception:
            recent_history = []

        assistant_text, prompt_tokens, completion_tokens = await self._call_llm(
            user_text=message_data.content,
            system_context=system_context,
            recent_history=recent_history,
        )

        assistant_message = await ChatMessageRepository.create_message(
            session=session,
            session_id=session_id,
            profile_id=profile_id,
            role="assistant",
            content=assistant_text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            citations=citations_payload,
        )

        try:
            await self.generate_and_update_chat_title(
                session=session,
                session_id=session_id,
                profile_id=profile_id,
                user_content=message_data.content,
                assistant_content=assistant_text,
            )
        except Exception:
            pass

        return assistant_message
    
    async def send_message_agentic(
        self,
        session: AsyncSession,
        session_id: UUID,
        profile_id: UUID,
        message_data: ChatMessageCreate,
    ) -> Dict[str, Any]:
        """Run the agentic Planner -> Executor -> Reviewer pipeline and persist final assistant reply.

        Returns a dict with plan, execution_result, review_result, and persisted assistant message
        (including citations and aggregated token usage).
        """
        if not getattr(settings, "agentic_chat_enabled", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Agentic chat mode is currently disabled by server configuration.",
            )

        # Persist user's message first
        await ChatMessageRepository.create_message(
            session=session,
            session_id=session_id,
            profile_id=profile_id,
            role="user",
            content=message_data.content,
        )

        # Prepare retrieval context (initial)
        system_context, final_citations = await self._retrieve_composed_context(
            session=session,
            query_text=message_data.content,
            profile_id=profile_id,
            folder_id=message_data.folder_id,
            top_k=5,
        )

        # Trim recent history similar to normal chat
        try:
            all_messages = await ChatMessageRepository.get_session_messages(
                session=session,
                session_id=session_id,
                profile_id=profile_id,
                skip=0,
                limit=100,
            )
            recent_history = self._trim_history_by_token_budget(all_messages, max_tokens=2000)
        except Exception:
            recent_history = []

        # Build plan using PlannerAgent
        from app.agents.planner import PlannerAgent
        from app.agents.executor import ExecutorAgent
        from app.agents.reviewer import ReviewerAgent
        from app.folders.repositories import FolderRepository

        # Try to include folder metadata to help planning
        try:
            folders = await FolderRepository.get_user_folders(session, profile_id)
            folder_list = [{"id": str(f.id), "name": f.name, "folder_type": getattr(f, "folder_type", "custom")} for f in folders]
        except Exception:
            folder_list = []

        planner = PlannerAgent(settings)
        plan = await planner.create_plan(message_data.content, context={"folders": folder_list, "system_context": system_context})

        # Hard cap on plan size to prevent runaway/malformed plans from triggering unbounded LLM calls
        truncated_info = None
        MAX_PLAN_STEPS = 8
        if len(plan.steps) > MAX_PLAN_STEPS:
            truncated_info = {
                "original_step_count": len(plan.steps),
                "truncated_to": MAX_PLAN_STEPS,
            }
            plan.steps = plan.steps[:MAX_PLAN_STEPS]

        planner_tokens = getattr(planner, "last_usage_tokens", {"prompt_tokens": 0, "completion_tokens": 0})

        # Execute plan
        executor = ExecutorAgent(settings)
        exec_context = {"session": session, "profile_id": profile_id, "folder_id": message_data.folder_id, "recent_history": recent_history, "user_text": message_data.content}
        execution_result = await executor.execute_plan(plan, context=exec_context)
        executor_tokens = getattr(executor, "last_usage_tokens", {"prompt_tokens": 0, "completion_tokens": 0})

        # Review execution
        reviewer = ReviewerAgent(settings)
        review_context = {"sample_context": system_context, "plan": plan}
        review_result = await reviewer.review_execution(execution_result, original_plan=plan, context=review_context)
        reviewer_tokens = getattr(reviewer, "last_usage_tokens", {"prompt_tokens": 0, "completion_tokens": 0})

        final_text = execution_result.output
        revision_tokens = {"prompt_tokens": 0, "completion_tokens": 0}

        # If reviewer requested changes (not approved), perform one revision pass
        if not review_result.success:
            # Ask LLM to revise the combined execution output according to review comments
            try:
                import litellm
                messages = []
                if system_context:
                    messages.append({"role": "system", "content": system_context})
                messages.append({"role": "user", "content": f"Original goal: {message_data.content}\n\nExecution output:\n{execution_result.output}\n\nReviewer comments:\n{review_result.metadata.get('comments') or review_result.output}\n\nPlease produce a revised, concise assistant reply that addresses the reviewer's concerns and cites any supporting context."})
                response = await litellm.acompletion(model=settings.llm_chat_model_name, messages=messages, api_key=settings.llm_api_key.get_secret_value())

                usage = getattr(response, "usage", None)
                if usage is None and isinstance(response, dict):
                    usage = response.get("usage")
                if usage is not None:
                    pt = getattr(usage, "prompt_tokens", None) if not isinstance(usage, dict) else usage.get("prompt_tokens")
                    ct = getattr(usage, "completion_tokens", None) if not isinstance(usage, dict) else usage.get("completion_tokens")
                    revision_tokens["prompt_tokens"] += int(pt or 0)
                    revision_tokens["completion_tokens"] += int(ct or 0)

                choices = getattr(response, "choices", None) or (response.get("choices") if isinstance(response, dict) else None)
                if choices:
                    first = choices[0]
                    message = getattr(first, "message", None) or (first.get("message") if isinstance(first, dict) else None)
                    content = getattr(message, "content", None) or (message.get("content") if isinstance(message, dict) else None)
                    if content is not None:
                        final_text = str(content)
            except Exception:
                # If revision fails, keep original execution result
                pass

        total_prompt_tokens = (
            planner_tokens.get("prompt_tokens", 0)
            + executor_tokens.get("prompt_tokens", 0)
            + reviewer_tokens.get("prompt_tokens", 0)
            + revision_tokens.get("prompt_tokens", 0)
        )
        total_completion_tokens = (
            planner_tokens.get("completion_tokens", 0)
            + executor_tokens.get("completion_tokens", 0)
            + reviewer_tokens.get("completion_tokens", 0)
            + revision_tokens.get("completion_tokens", 0)
        )

        # Persist final assistant message with aggregated token totals
        assistant_message = await ChatMessageRepository.create_message(
            session=session,
            session_id=session_id,
            profile_id=profile_id,
            role="assistant",
            content=final_text,
            prompt_tokens=total_prompt_tokens,
            completion_tokens=total_completion_tokens,
            citations=final_citations,
        )

        try:
            await self.generate_and_update_chat_title(
                session=session,
                session_id=session_id,
                profile_id=profile_id,
                user_content=message_data.content,
                assistant_content=final_text,
            )
        except Exception:
            pass

        # Build return payload describing the pipeline
        # Sanitize execution and review outputs to ensure JSON serializability
        exec_dump = execution_result.model_dump()
        exec_meta = exec_dump.get("metadata") or {}
        if isinstance(exec_meta, dict) and exec_meta.get("context"):
            ctx = exec_meta.get("context")
            if isinstance(ctx, dict) and "session" in ctx:
                ctx.pop("session", None)
            exec_meta["context"] = ctx
            exec_dump["metadata"] = exec_meta

        review_dump = review_result.model_dump()
        review_meta = review_dump.get("metadata") or {}
        if isinstance(review_meta, dict) and review_meta.get("plan"):
            # Remove any non-serializable entries from plan in review metadata
            review_meta.pop("plan", None)
            review_dump["metadata"] = review_meta

        result_payload: Dict[str, Any] = {
            "plan": plan.model_dump(),
            "execution": exec_dump,
            "review": review_dump,
            "assistant_message": {
                "id": str(assistant_message.id),
                "content": assistant_message.content,
                "citations": final_citations,
                "prompt_tokens": total_prompt_tokens,
                "completion_tokens": total_completion_tokens,
            },
            "token_usage": {
                "planner": planner_tokens,
                "executor": executor_tokens,
                "reviewer": reviewer_tokens,
                "revision": revision_tokens,
                "total_prompt_tokens": total_prompt_tokens,
                "total_completion_tokens": total_completion_tokens,
            },
        }

        if truncated_info:
            result_payload["truncated"] = truncated_info

        return result_payload

    async def _call_llm(
        self,
        user_text: str,
        system_context: str,
        recent_history: List[Any],
    ) -> tuple[str, Optional[int], Optional[int]]:
        """Call the configured LiteLLM provider and return response text and token metrics."""
        import litellm

        messages: List[Dict[str, str]] = []
        if system_context:
            messages.append({"role": "system", "content": system_context})

        for message in recent_history:
            role = getattr(message, "role", None) or "user"
            content = getattr(message, "content", "")
            messages.append({"role": str(role), "content": str(content)})

        messages.append({"role": "user", "content": user_text})

        try:
            response = await litellm.acompletion(
                model=settings.llm_chat_model_name,
                messages=messages,
                api_key=settings.llm_api_key.get_secret_value(),
            )
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"LLM provider error: {str(exc)}") from exc

        choices = getattr(response, "choices", None)
        if choices is None and isinstance(response, dict):
            choices = response.get("choices")
        if not choices:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="LLM provider error: empty completion response")

        first_choice = choices[0]
        message = getattr(first_choice, "message", None)
        if message is None and isinstance(first_choice, dict):
            message = first_choice.get("message")
        content = getattr(message, "content", None) if message is not None else None
        if content is None and isinstance(message, dict):
            content = message.get("content")
        if content is None:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="LLM provider error: missing response content")

        usage = getattr(response, "usage", None)
        if usage is None and isinstance(response, dict):
            usage = response.get("usage")
        prompt_tokens = getattr(usage, "prompt_tokens", None) if usage is not None else None
        completion_tokens = getattr(usage, "completion_tokens", None) if usage is not None else None
        if prompt_tokens is None and isinstance(usage, dict):
            prompt_tokens = usage.get("prompt_tokens")
        if completion_tokens is None and isinstance(usage, dict):
            completion_tokens = usage.get("completion_tokens")

        return (
            str(content),
            int(prompt_tokens) if prompt_tokens is not None else None,
            int(completion_tokens) if completion_tokens is not None else None,
        )

    @staticmethod
    def _trim_history_by_token_budget(messages: List[Any], max_tokens: int = 2000) -> List[Any]:
        """Return the most recent messages that fit within an approximate token budget.

        Walks backward from the newest message, accumulating a rough token estimate
        (~4 characters per token, the standard rule of thumb for English text) until
        the budget is used up. Always includes at least the single most recent
        message, even if it alone exceeds the budget, so history is never silently
        dropped to zero.
        """
        selected: List[Any] = []
        running_tokens = 0

        for message in reversed(messages):
            content = getattr(message, "content", "") or ""
            estimated_tokens = max(1, len(content) // 4)

            if selected and running_tokens + estimated_tokens > max_tokens:
                break

            selected.append(message)
            running_tokens += estimated_tokens

        selected.reverse()  # restore chronological order (oldest to newest)
        return selected


    async def stream_message(
        self,
        session: AsyncSession,
        session_id: UUID,
        profile_id: UUID,
        message_data: ChatMessageCreate,
    ):
        """Stream LLM tokens to the client via an async generator of SSE-formatted strings.

        Follows the same retrieval and context-building steps as send_message(), then calls
        litellm.acompletion(..., stream=True) and yields incremental token events. After the
        stream completes (or on error), persists the assistant message and yields a final
        "done" event with metadata.
        """
        import json
        import litellm

        chat_session = await ChatSessionRepository.get_session_by_id(session=session, session_id=session_id, profile_id=profile_id)
        if chat_session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")

        # Persist user's message first (so conversation state is recorded immediately)
        await ChatMessageRepository.create_message(
            session=session,
            session_id=session_id,
            profile_id=profile_id,
            role="user",
            content=message_data.content,
        )

        system_context, citations_payload = await self._retrieve_composed_context(
            session=session,
            query_text=message_data.content,
            profile_id=profile_id,
            folder_id=message_data.folder_id,
            top_k=message_data.top_k or 5,
        )

        try:
            all_messages = await ChatMessageRepository.get_session_messages(
                session=session,
                session_id=session_id,
                profile_id=profile_id,
                skip=0,
                limit=100,
            )
            recent_history = self._trim_history_by_token_budget(all_messages, max_tokens=2000)
        except Exception:
            recent_history = []

        # Build the messages array for the LLM (identical to _call_llm)
        messages: List[Dict[str, str]] = []
        if system_context:
            messages.append({"role": "system", "content": system_context})

        for message in recent_history:
            role = getattr(message, "role", None) or "user"
            content = getattr(message, "content", "")
            messages.append({"role": str(role), "content": str(content)})

        messages.append({"role": "user", "content": message_data.content})

        # Call LLM in streaming mode
        try:
            stream = await litellm.acompletion(
                model=settings.llm_chat_model_name,
                messages=messages,
                api_key=settings.llm_api_key.get_secret_value(),
                stream=True,
            )
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"LLM provider error: {str(exc)}") from exc

        accumulated = ""
        last_usage = None

        # The stream may be an async generator of chunks
        try:
            async for chunk in stream:
                # Extract incremental content safely from provider-specific structures
                choices = getattr(chunk, "choices", None)
                if choices is None and isinstance(chunk, dict):
                    choices = chunk.get("choices")
                if not choices:
                    # some streamed chunks are heartbeats or metadata; skip
                    continue

                first = choices[0]
                delta = getattr(first, "delta", None) if first is not None else None
                if delta is None and isinstance(first, dict):
                    delta = first.get("delta")

                text = None
                if delta is not None:
                    text = getattr(delta, "content", None) if not isinstance(delta, dict) else delta.get("content")

                if text:
                    # accumulate and yield as an SSE token event
                    accumulated += str(text)
                    yield f"data: {json.dumps({'type': 'token', 'content': str(text)})}\n\n"

                # Capture any usage info if included in the final chunk
                usage = getattr(chunk, "usage", None) if not isinstance(chunk, dict) else chunk.get("usage")
                if usage:
                    last_usage = usage

        except Exception as stream_exc:
            # On stream failure, attempt to persist partial content to avoid data loss,
            # then yield an error event so the client can handle it gracefully.
            try:
                partial_message = await ChatMessageRepository.create_message(
                    session=session,
                    session_id=session_id,
                    profile_id=profile_id,
                    role="assistant",
                    content=accumulated,
                    prompt_tokens=None,
                    completion_tokens=None,
                    citations=citations_payload,
                )
                # Notify client of the error and include partial message id so client can reference it
                yield f"data: {json.dumps({'type': 'error', 'detail': str(stream_exc), 'partial_message_id': str(partial_message.id)})}\n\n"
            except Exception:
                # If we fail to persist, still send an error event
                yield f"data: {json.dumps({'type': 'error', 'detail': 'LLM stream failed and partial message could not be persisted'})}\n\n"
            return

        # Stream completed successfully — persist the full assistant message

        # Extract tokens from last_usage when available
        prompt_tokens = None
        completion_tokens = None
        if last_usage is not None:
            if hasattr(last_usage, "prompt_tokens"):
                prompt_tokens = getattr(last_usage, "prompt_tokens")
            elif isinstance(last_usage, dict):
                prompt_tokens = last_usage.get("prompt_tokens")

            if hasattr(last_usage, "completion_tokens"):
                completion_tokens = getattr(last_usage, "completion_tokens")
            elif isinstance(last_usage, dict):
                completion_tokens = last_usage.get("completion_tokens")

        assistant_message = await ChatMessageRepository.create_message(
            session=session,
            session_id=session_id,
            profile_id=profile_id,
            role="assistant",
            content=accumulated,
            prompt_tokens=int(prompt_tokens) if prompt_tokens is not None else None,
            completion_tokens=int(completion_tokens) if completion_tokens is not None else None,
            citations=citations_payload,
        )

        try:
            await self.generate_and_update_chat_title(
                session=session,
                session_id=session_id,
                profile_id=profile_id,
                user_content=message_data.content,
                assistant_content=accumulated,
            )
        except Exception:
            pass

        # Final done event with metadata
        yield f"data: {json.dumps({'type': 'done', 'message_id': str(assistant_message.id), 'citations': citations_payload, 'prompt_tokens': prompt_tokens, 'completion_tokens': completion_tokens})}\n\n"

    @staticmethod
    async def generate_and_update_chat_title(
        session: AsyncSession,
        session_id: UUID,
        profile_id: UUID,
        user_content: str,
        assistant_content: str,
    ) -> Optional[str]:
        """Generate a concise 3-5 word title for the chat session based on the first message exchange."""
        import litellm

        try:
            chat_session = await ChatSessionRepository.get_session_by_id(session=session, session_id=session_id, profile_id=profile_id)
            if not chat_session:
                return None
            current_title = (chat_session.title or "").strip()
            if current_title and current_title not in ("New Chat", "Untitled", ""):
                return current_title

            prompt = (
                "You are an AI assistant that writes concise, descriptive titles for chat conversations.\n"
                "Based on the following first exchange, write a title that is exactly 3 to 5 words long.\n"
                "Return ONLY the title text. Do NOT use quotes, markdown, punctuation, or preamble.\n\n"
                f"User: {user_content[:300]}\n\n"
                f"Assistant: {assistant_content[:300]}"
            )

            response = await litellm.acompletion(
                model=settings.llm_chat_model_name,
                messages=[{"role": "user", "content": prompt}],
                api_key=settings.llm_api_key.get_secret_value(),
            )

            choices = getattr(response, "choices", None) or (response.get("choices") if isinstance(response, dict) else None)
            if choices:
                first = choices[0]
                msg = getattr(first, "message", None) or (first.get("message") if isinstance(first, dict) else None)
                content = getattr(msg, "content", None) or (msg.get("content") if isinstance(msg, dict) else None)
                if content:
                    generated_title = str(content).strip().strip('"').strip("'").strip()
                    generated_title = generated_title.rstrip(".:;!?")
                    if generated_title:
                        words = generated_title.split()[:6]
                        clean_title = " ".join(words)
                        update_payload = ChatSessionUpdate(title=clean_title)
                        await ChatSessionRepository.update_session(session=session, chat_session=chat_session, update_data=update_payload)
                        return clean_title
        except Exception:
            try:
                words = user_content.strip().split()[:5]
                fallback_title = " ".join(words) if words else "New Chat"
                if chat_session and chat_session.title in ("New Chat", "Untitled", ""):
                    update_payload = ChatSessionUpdate(title=fallback_title)
                    await ChatSessionRepository.update_session(session=session, chat_session=chat_session, update_data=update_payload)
                    return fallback_title
            except Exception:
                pass
        return None


__all__ = ["ChatService"]
