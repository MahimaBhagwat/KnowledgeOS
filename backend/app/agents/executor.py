from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.agents.core import AgentExecutionResult, AgentPlan, AgentStep, BaseAgent


class ExecutorAgent(BaseAgent):
    """Agent responsible for executing an AgentPlan step-by-step.

    This executor reuses the project's SemanticRetriever and litellm to perform
    step-level retrieval and generation. The context object passed into run()
    must include:
      - session: SQLAlchemy AsyncSession for DB retrieval
      - profile_id: UUID of the requesting profile
      - folder_id: optional folder scope
      - recent_history: optional chat history
      - user_text: original user query

    After execute_plan() runs, self.last_usage_tokens holds the SUM of
    prompt/completion tokens across every generation-step LLM call made
    during that execution (0/0 if no generation steps ran an LLM call).
    """

    async def run(self, input_text: str, context: Optional[dict] = None) -> AgentExecutionResult:
        # Attempt to parse a serialized JSON AgentPlan
        plan: AgentPlan
        try:
            payload = json.loads(input_text)
            # If payload looks like a plan, try to validate
            if isinstance(payload, dict) and payload.get("goal") and payload.get("steps"):
                plan = AgentPlan.model_validate(payload)
            else:
                # Not a plan structure; fall back to single step plan
                plan = AgentPlan(goal=input_text.strip() or "(no goal)", steps=[AgentStep(step_number=1, action="task", description=input_text.strip() or "(no description)")])
        except Exception:
            # Not JSON or failed validation — build single-step plan
            plan = AgentPlan(goal=input_text.strip() or "(no goal)", steps=[AgentStep(step_number=1, action="task", description=input_text.strip() or "(no description)")])

        return await self.execute_plan(plan, context=context)

    async def execute_plan(self, plan: AgentPlan, context: Optional[dict] = None) -> AgentExecutionResult:
        """Execute a structured AgentPlan sequentially.

        Each step is executed via _execute_step which uses retrieval + generation
        where applicable. The method collects per-step outputs and timing metadata,
        and accumulates token usage across all steps into self.last_usage_tokens.
        """
        self.last_usage_tokens: Dict[str, int] = {"prompt_tokens": 0, "completion_tokens": 0}

        task_id = f"exec_{uuid4().hex[:8]}"
        start_time = time.time()
        outputs: List[str] = []
        executed_steps: List[Dict[str, Any]] = []

        for step in plan.steps:
            step_start = time.time()
            try:
                success, result_text = await self._execute_step(step, context=context)
            except Exception as exc:  # pragma: no cover - defensive
                success = False
                result_text = f"Step execution raised an exception: {exc}"

            step_end = time.time()
            step.completed = bool(success)

            outputs.append(f"Step {step.step_number}: {result_text}")
            executed_steps.append(
                {
                    "step_number": int(step.step_number),
                    "action": step.action,
                    "description": step.description,
                    "completed": bool(success),
                    "duration_seconds": step_end - step_start,
                }
            )

        end_time = time.time()
        total_duration = end_time - start_time
        all_success = all(s.get("completed", False) for s in executed_steps)

        output_text = "\n".join(outputs).strip()
        metadata: Dict[str, Any] = {
            "executed_steps": executed_steps,
            "total_steps": len(plan.steps),
            "start_time": start_time,
            "end_time": end_time,
            "duration_seconds": total_duration,
            "context": context or {},
        }

        return AgentExecutionResult(task_id=task_id, success=all_success, output=output_text, metadata=metadata)

    def _accumulate_usage(self, response: Any) -> None:
        """Extract prompt/completion tokens from a litellm response and add to last_usage_tokens."""
        usage = getattr(response, "usage", None)
        if usage is None and isinstance(response, dict):
            usage = response.get("usage")
        if usage is None:
            return
        prompt_tokens = getattr(usage, "prompt_tokens", None) if not isinstance(usage, dict) else usage.get("prompt_tokens")
        completion_tokens = getattr(usage, "completion_tokens", None) if not isinstance(usage, dict) else usage.get("completion_tokens")
        self.last_usage_tokens["prompt_tokens"] += int(prompt_tokens or 0)
        self.last_usage_tokens["completion_tokens"] += int(completion_tokens or 0)

    async def _execute_step(self, step: AgentStep, context: Optional[dict] = None) -> tuple[bool, str]:
        """Execute a single plan step using retrieval and LLM generation where appropriate.

        Behavior by action label (heuristic):
          - 'review_context' or 'analyze': perform a retrieval using the step.description as query and return the concatenated contexts
          - 'implement', 'task', or others: call the LLM to produce a focused answer for this step using retrieved context
        """
        # Lazy import to avoid heavy dependencies at module import time
        from app.retrieval.retriever import SemanticRetriever
        from app.notes.retriever import NoteRetriever
        from app.core.embeddings import generate_query_embedding
        import litellm
        from app.core.config import settings

        session = None
        profile_id = None
        folder_id = None
        recent_history = []
        user_text = None
        if context:
            session = context.get("session")
            profile_id = context.get("profile_id")
            folder_id = context.get("folder_id")
            recent_history = context.get("recent_history") or []
            user_text = context.get("user_text")

        retriever = SemanticRetriever()
        note_retriever = NoteRetriever()

        async def _get_composed_context(query_str: str):
            try:
                q_emb = generate_query_embedding(query_str)
            except Exception:
                q_emb = []
            doc_ctxs = []
            note_ctxs = []
            if session and profile_id and q_emb:
                try:
                    doc_ctxs = await retriever.retrieve_relevant_chunks(
                        session=session,
                        query_embedding=q_emb,
                        profile_id=profile_id,
                        folder_id=folder_id,
                        top_k=5,
                    )
                except Exception:
                    doc_ctxs = []
                try:
                    note_ctxs = await note_retriever.retrieve_relevant_chunks(
                        session=session,
                        query_embedding=q_emb,
                        profile_id=profile_id,
                        folder_id=folder_id,
                        top_k=5,
                    )
                except Exception:
                    note_ctxs = []
            doc_formatted = retriever.format_context_for_llm(doc_ctxs)
            note_formatted = note_retriever.format_context_for_llm(note_ctxs)
            sections = []
            if doc_formatted:
                sections.append(f"--- Document Knowledge ---\n{doc_formatted}")
            if note_formatted:
                sections.append(f"--- User Notes ---\n{note_formatted}")
            return "\n\n".join(sections).strip(), doc_ctxs, note_ctxs

        # If the step is inspection/review, perform retrieval and return formatted context
        if step.action in ("review_context", "analyze"):
            try:
                query_text = step.description or user_text or ""
                formatted, _, _ = await _get_composed_context(query_text)
                if not formatted:
                    return True, "No relevant context found."
                return True, f"Retrieved context:\n{formatted}"
            except Exception as exc:
                return False, f"Retrieval failed: {exc}"

        # For generation-like steps, call LLM with retrieved context and prompt for a concise result
        try:
            query_text = step.description or user_text or ""
            system_context, doc_contexts, note_contexts = await _get_composed_context(query_text)

            messages: List[dict] = []
            if system_context:
                messages.append({"role": "system", "content": system_context})

            # Include recent history lightly to provide continuity
            for m in (recent_history or []):
                messages.append({"role": getattr(m, "role", "user"), "content": getattr(m, "content", "")})

            # Prompt the LLM to perform the step
            user_prompt = f"Perform the following step from a plan: {step.description}. Provide a concise, finalizable output for this step."
            if user_text:
                user_prompt = f"Original goal: {user_text}\n\nStep: {step.description}\nProvide the best possible response leveraging the provided contexts."

            messages.append({"role": "user", "content": user_prompt})

            response = await litellm.acompletion(model=settings.llm_chat_model_name, messages=messages, api_key=settings.llm_api_key.get_secret_value())

            self._accumulate_usage(response)

            choices = getattr(response, "choices", None) or (response.get("choices") if isinstance(response, dict) else None)
            if not choices:
                return False, "LLM returned no choices"
            first = choices[0]
            message = getattr(first, "message", None) or (first.get("message") if isinstance(first, dict) else None)
            content = getattr(message, "content", None) or (message.get("content") if isinstance(message, dict) else None)
            if content is None:
                return False, "LLM produced empty content"

            # Return the step output and success
            # Also include a short citation summary if contexts exist
            citations_list = []
            for c in doc_contexts[:2]:
                citations_list.append(f"doc:{str(c.document_id)[:8]}:chunk{c.chunk_index}")
            for n in note_contexts[:2]:
                citations_list.append(f"note:{str(n.note_id)[:8]}:chunk{n.chunk_index}")
            citation_summary = ", ".join(citations_list) if citations_list else None

            result_text = str(content).strip()
            if citation_summary:
                result_text = f"{result_text}\n\nCitations: {citation_summary}"
            return True, result_text
        except Exception as exc:
            return False, f"Execution error: {exc}"


__all__ = ["ExecutorAgent"]
