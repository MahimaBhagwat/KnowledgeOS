from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel

from app.agents.core import AgentExecutionResult, AgentPlan, BaseAgent


class ReviewerAgent(BaseAgent):
    """Agent that evaluates execution results for quality, completeness, and formatting.

    This reviewer uses the LLM to produce a critique of the execution output
    relative to the original plan and the retrieved context. If the reviewer
    requests changes, the executor is allowed a single revision pass.
    """

    REVIEW_THRESHOLD: float = 0.7

    async def run(self, input_text: str, context: Optional[dict] = None) -> AgentExecutionResult:
        """Evaluate a serialized AgentExecutionResult or plain execution output.

        Attempts to deserialize input_text as JSON. If successful and the payload
        resembles AgentExecutionResult, it is validated and reviewed. Otherwise,
        a simple report is produced marking the input as unparseable.
        """
        try:
            payload = json.loads(input_text)
        except Exception:
            return AgentExecutionResult(
                task_id=f"review_{uuid4().hex[:8]}",
                success=False,
                output="Input could not be parsed as a serialized AgentExecutionResult.",
                metadata={"parsed": False},
            )

        # Validate minimal shape
        task_id = payload.get("task_id") or payload.get("metadata", {}).get("task_id")
        try:
            if isinstance(payload, dict) and payload.get("task_id"):
                # Use the core model to normalize structure where possible
                exec_result = AgentExecutionResult.model_validate(payload)
            else:
                # Fallback: attempt to construct a minimal AgentExecutionResult
                exec_result = AgentExecutionResult(
                    task_id=str(task_id or f"exec_{uuid4().hex[:8]}"),
                    success=bool(payload.get("success", False)),
                    output=str(payload.get("output", "")),
                    metadata=payload.get("metadata", {}) or {},
                )
        except Exception:
            return AgentExecutionResult(
                task_id=f"review_{uuid4().hex[:8]}",
                success=False,
                output="Payload was not a valid AgentExecutionResult structure.",
                metadata={"parsed": False},
            )

        return await self.review_execution(exec_result, original_plan=context.get("plan") if context else None, context=context)

    async def review_execution(
        self, execution_result: AgentExecutionResult, original_plan: Optional[AgentPlan] = None, context: Optional[dict] = None
    ) -> AgentExecutionResult:
        """Evaluate an AgentExecutionResult and return a review result.

        This version uses the LLM to critique the execution. The LLM is given
        the execution output, the original plan (if available), and a small
        sample of retrieved context to ground its critique.
        """
        # Use available short context for the reviewer (if retriever results passed)
        sample_context_text = ""
        if context:
            sample_context_text = context.get("sample_context") or ""

        # Compose a critique prompt
        try:
            import litellm
            from app.core.config import settings

            user_prompt = (
                "You are a reviewer. Given the original plan and the execution output,\n"
                "assess whether the output answers the user's goal, cites relevant sources,\n"
                "and avoids unsupported claims. Return a short JSON with: {\n"
                "  'decision': 'approve' or 'revise',\n"
                "  'score': float between 0 and 1,\n"
                "  'comments': string\n"
                "}\n"
                "Also include a brief actionable suggestion if decision == 'revise'.\n"
            )

            messages = [
                {"role": "system", "content": "You are an expert reviewer checking factuality and citation coverage."},
                {"role": "user", "content": f"Plan: {json.dumps(original_plan.model_dump() if original_plan else {})}\n\nExecution Output: {execution_result.output}\n\nContext: {sample_context_text}"},
            ]

            response = await litellm.acompletion(model=settings.llm_chat_model_name, messages=messages, api_key=settings.llm_api_key.get_secret_value())
            choices = getattr(response, "choices", None) or (response.get("choices") if isinstance(response, dict) else None)
            if not choices:
                raise ValueError("LLM returned no choices for review")
            first = choices[0]
            message = getattr(first, "message", None) or (first.get("message") if isinstance(first, dict) else None)
            content = getattr(message, "content", None) or (message.get("content") if isinstance(message, dict) else None)
            if content is None:
                raise ValueError("LLM review returned empty content")

            # Try to extract JSON from LLM reply
            json_text = content.strip()
            # Attempt to find a JSON object within the reply
            start = json_text.find("{")
            end = json_text.rfind("}")
            decision = "revise"
            score = 0.0
            comments = str(content)
            try:
                if start != -1 and end != -1 and end > start:
                    parsed = json.loads(json_text[start : end + 1])
                    decision = parsed.get("decision") or parsed.get("status") or ("approve" if parsed.get("score", 0) >= 0.7 else "revise")
                    score = float(parsed.get("score", 0.0))
                    comments = parsed.get("comments") or parsed.get("notes") or comments
                else:
                    # If not parseable, fall back to heuristic
                    lowered = content.lower()
                    if "approve" in lowered or "looks good" in lowered:
                        decision = "approve"
                        score = 0.8
                    else:
                        decision = "revise"
                        score = 0.4
            except Exception:
                decision = "revise"
                score = 0.0

            is_approved = decision == "approve" or score >= self.REVIEW_THRESHOLD

            report = f"Review decision: {decision}\nScore: {score:.2f}\nComments: {comments}"
            metadata = {"decision": decision, "score": float(score), "comments": comments}
            return AgentExecutionResult(task_id=f"review_{uuid4().hex[:8]}", success=is_approved, output=report, metadata=metadata)

        except Exception as exc:
            # Fallback to heuristic reviewer if LLM fails
            # Reuse earlier deterministic scoring logic
            metadata: Dict[str, Any] = execution_result.metadata or {}
            executed_steps: List[Dict[str, Any]] = metadata.get("executed_steps") or []

            total_steps = len(executed_steps)
            if total_steps > 0:
                completed_count = sum(1 for s in executed_steps if s.get("completed"))
                step_score = completed_count / total_steps
            else:
                step_score = 1.0 if execution_result.success else 0.0

            output_text = (execution_result.output or "").strip()
            if not output_text:
                output_score = 0.0
            else:
                length = len(output_text)
                if length < 50:
                    output_score = 0.4
                elif length < 200:
                    output_score = 0.7
                else:
                    output_score = 0.9

            formatting_bonus = 0.0
            if "Step" in output_text or "-" in output_text or "[" in output_text:
                formatting_bonus = 0.05

            negative_indicators = ("error", "exception", "failed", "traceback")
            penalty = 0.0
            lowered = output_text.lower()
            if any(ind in lowered for ind in negative_indicators):
                penalty = 0.2

            quality_score = max(0.0, min(1.0, (0.7 * step_score) + (0.25 * output_score) + formatting_bonus - penalty))
            is_approved = quality_score >= self.REVIEW_THRESHOLD

            report_lines: List[str] = []
            report_lines.append(f"Review for task {execution_result.task_id} (fallback):")
            report_lines.append(f"Quality score: {quality_score:.2f}")
            report_lines.append("Status: " + ("APPROVED" if is_approved else "CHANGES_REQUESTED"))
            report = "\n".join(report_lines)
            return AgentExecutionResult(task_id=f"review_{uuid4().hex[:8]}", success=is_approved, output=report, metadata={"quality_score": quality_score})


__all__ = ["ReviewerAgent"]
