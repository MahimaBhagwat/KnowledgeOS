"""Agent abstractions and execution data structures."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class AgentStep(BaseModel):
    """A single ordered step within an agent plan."""

    step_number: int = Field(..., ge=0)
    action: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    completed: bool = False

    model_config = ConfigDict(from_attributes=True)


class AgentPlan(BaseModel):
    """A structured plan describing how an agent should execute a goal."""

    goal: str = Field(..., min_length=1)
    steps: List[AgentStep]

    model_config = ConfigDict(from_attributes=True)


class AgentExecutionResult(BaseModel):
    """Outcome returned by an agent execution run."""

    task_id: str = Field(..., min_length=1)
    success: bool
    output: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class BaseAgent(ABC):
    """Abstract base class for multi-agent execution workflows."""

    def __init__(self, settings: Any) -> None:
        self._settings = settings

    @property
    def settings(self) -> Any:
        """Return the agent configuration object."""
        return self._settings

    @abstractmethod
    async def run(self, input_text: str, context: Optional[dict] = None) -> AgentExecutionResult:
        """Execute the agent against the provided input and optional context."""
        raise NotImplementedError


__all__ = [
    "AgentExecutionResult",
    "AgentPlan",
    "AgentStep",
    "BaseAgent",
]
