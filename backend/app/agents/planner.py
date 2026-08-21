from __future__ import annotations

import json
import re
from uuid import uuid4
from typing import Any, Dict, List, Optional

from app.agents.core import AgentExecutionResult, AgentPlan, AgentStep, BaseAgent


class PlannerAgent(BaseAgent):
    """Agent responsible for decomposing a goal into executable steps.

    This implementation uses the configured LLM to generate a structured JSON
    plan when heuristic parsing is insufficient. The LLM is asked to produce a
    compact JSON object with `goal` and `steps` where each step contains
    `step_number`, `action`, and `description` fields. If the LLM call fails
    or returns invalid JSON, the planner falls back to the previous heuristic
    behavior.
    """

    async def create_plan(self, goal: str, context: Optional[dict] = None) -> AgentPlan:
        """Create a structured plan from a goal string and optional context.

        First attempt to parse structured steps from the input; if none are
        present attempt to ask the LLM to produce a JSON plan. On error,
        fall back to heuristic plan building.
        """
        normalized_goal = goal.strip()
        steps = self._parse_structured_steps(normalized_goal)
        if steps:
            return AgentPlan(goal=normalized_goal, steps=steps)

        # Attempt LLM-based plan generation
        try:
            import litellm
            from app.core.config import settings

            # Provide some surrounding context to the planner: available folders
            folder_list = []
            if context and isinstance(context.get("folders"), list):
                folder_list = [f.get("name") for f in context.get("folders") if isinstance(f, dict) and f.get("name")]

            system_prompt_lines = [
                "You are a planning assistant. Given a user's goal, decompose it into a short ordered plan.",
                "Return ONLY a JSON object with two keys: 'goal' (string) and 'steps' (array).",
                "Each step must include: step_number (int), action (short label), description (string).",
            ]
            if folder_list:
                system_prompt_lines.append(f"Available folders: {', '.join(folder_list)}")

            messages = [
                {"role": "system", "content": "\n".join(system_prompt_lines)},
                {"role": "user", "content": f"Create a plan for the following goal:\n{normalized_goal}"},
            ]

            response = await litellm.acompletion(model=settings.llm_chat_model_name, messages=messages, api_key=settings.llm_api_key.get_secret_value())

            # Extract content safely
            choices = getattr(response, "choices", None) or (response.get("choices") if isinstance(response, dict) else None)
            if not choices:
                raise ValueError("LLM returned no choices for plan generation")
            first = choices[0]
            message = getattr(first, "message", None) or (first.get("message") if isinstance(first, dict) else None)
            content = getattr(message, "content", None) or (message.get("content") if isinstance(message, dict) else None)
            if content is None:
                raise ValueError("LLM plan generation returned empty content")

            # The LLM may include markdown/text around JSON; extract JSON object
            json_text = self._extract_json_block(str(content))
            payload = json.loads(json_text)
            steps_payload = payload.get("steps") or []
            steps: List[AgentStep] = []
            for s in steps_payload:
                try:
                    steps.append(
                        AgentStep(
                            step_number=int(s.get("step_number", len(steps) + 1)),
                            action=str(s.get("action", "task")),
                            description=str(s.get("description", "")),
                            completed=False,
                        )
                    )
                except Exception:
                    # Skip malformed step entries
                    continue

            if not steps:
                raise ValueError("Parsed plan contained no valid steps")

            return AgentPlan(goal=normalized_goal, steps=steps)

        except Exception:
            # On any failure, fall back to heuristic plan builder
            steps = self._build_heuristic_steps(normalized_goal, context)
            return AgentPlan(goal=normalized_goal, steps=steps)

    async def run(self, input_text: str, context: Optional[dict] = None) -> AgentExecutionResult:
        """Generate a plan for the provided input text."""
        plan = await self.create_plan(input_text, context)
        task_id = f"plan_{uuid4().hex[:8]}"
        output = json.dumps(plan.model_dump(), ensure_ascii=False)
        metadata: Dict[str, Any] = {
            "plan": plan.model_dump(),
            "step_count": len(plan.steps),
            "context": context or {},
        }
        return AgentExecutionResult(
            task_id=task_id,
            success=True,
            output=output,
            metadata=metadata,
        )

    @staticmethod
    def _extract_json_block(text: str) -> str:
        """Extract the first JSON object found in text. If none found, return text as-is.

        Helps tolerate LLM responses wrapped in markdown or explanatory text.
        """
        # Try a conservative approach: find outermost braces pair
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return text[start : end + 1]
        # Fallback: try to find a JSON array containing 'steps'
        arr_start = text.find("[")
        arr_end = text.rfind("]")
        if arr_start != -1 and arr_end != -1 and arr_end > arr_start:
            return text[arr_start : arr_end + 1]
        return text

    @staticmethod
    def _parse_structured_steps(goal: str) -> List[AgentStep]:
        """Parse enumerated or bullet-style steps from structured input."""
        lines = [line.strip() for line in goal.splitlines() if line.strip()]
        if len(lines) <= 1:
            return []

        steps: List[AgentStep] = []
        for line in lines[1:]:
            match = re.match(r"^(?:[-*]|\d+[).:-])\s*(.+)$", line)
            if match:
                step_text = match.group(1).strip()
                steps.append(
                    AgentStep(
                        step_number=len(steps) + 1,
                        action=PlannerAgent._infer_action(step_text),
                        description=step_text,
                        completed=False,
                    )
                )

        return steps

    @staticmethod
    def _build_heuristic_steps(goal: str, context: Optional[dict] = None) -> List[AgentStep]:
        """Build a simple heuristic plan when structured steps are unavailable."""
        steps: List[AgentStep] = []

        context_keys = sorted((context or {}).keys())
        if context_keys:
            steps.append(
                AgentStep(
                    step_number=1,
                    action="review_context",
                    description=f"Review available context: {', '.join(context_keys)}",
                    completed=False,
                )
            )

        goal_fragments = PlannerAgent._split_goal(goal)
        if not goal_fragments:
            goal_fragments = [goal]

        for fragment in goal_fragments:
            steps.append(
                AgentStep(
                    step_number=len(steps) + 1,
                    action=PlannerAgent._infer_action(fragment),
                    description=fragment,
                    completed=False,
                )
            )

        return steps

    @staticmethod
    def _split_goal(goal: str) -> List[str]:
        """Split a goal into coarse fragments for heuristic planning."""
        text = goal.strip()
        if not text:
            return []

        separators = [" and then ", " then ", " and ", ";", "."]
        fragments = [text]
        for separator in separators:
            next_fragments: List[str] = []
            for fragment in fragments:
                parts = [part.strip() for part in fragment.split(separator) if part.strip()]
                if len(parts) > 1:
                    next_fragments.extend(parts)
                else:
                    next_fragments.append(fragment)
            fragments = next_fragments

        unique_fragments: List[str] = []
        for fragment in fragments:
            if fragment and fragment not in unique_fragments:
                unique_fragments.append(fragment)
        return unique_fragments

    @staticmethod
    def _infer_action(text: str) -> str:
        """Infer a concise action label from a step description."""
        lowered = text.strip().lower()
        if lowered.startswith(("create ", "build ", "implement ", "write ")):
            return "implement"
        if lowered.startswith(("test ", "verify ", "validate ", "check ")):
            return "verify"
        if lowered.startswith(("read ", "review ", "inspect ", "analyze ")):
            return "analyze"
        if lowered.startswith(("update ", "modify ", "edit ", "change ")):
            return "update"
        if lowered.startswith(("delete ", "remove ")):
            return "delete"
        return "task"


__all__ = ["PlannerAgent"]
