from __future__ import annotations

from typing import List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Flashcard(BaseModel):
    question: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)

    model_config = ConfigDict(from_attributes=True)


class DocumentInsightsResponse(BaseModel):
    document_id: UUID
    summary: str
    key_takeaways: List[str]
    flashcards: List[Flashcard]

    model_config = ConfigDict(from_attributes=True)


class TopicSynthesis(BaseModel):
    """Synthesis of overarching themes and connections across multiple documents."""

    title: str = Field(..., description="Overall synthesized topic or domain name")
    overview: str = Field(..., description="Executive synthesis connecting the documents")
    connected_themes: List[str] = Field(default_factory=list, description="Major themes found across documents")
    key_concepts: List[str] = Field(default_factory=list, description="Core concepts and principles")

    model_config = ConfigDict(from_attributes=True)


class KnowledgeGap(BaseModel):
    """An identified gap, missing prerequisite, or contradiction in the knowledge collection."""

    topic: str = Field(..., description="Topic or area with missing information")
    description: str = Field(..., description="Why this is a gap or what is missing")
    recommendation: str = Field(..., description="Recommended reading or concept to study")
    severity: str = Field("medium", description="'low', 'medium', or 'high'")

    model_config = ConfigDict(from_attributes=True)


class LearningRoadmapItem(BaseModel):
    """A structured milestone in a generated learning roadmap."""

    step: int = Field(..., description="Step sequence index (1-based)")
    title: str = Field(..., description="Milestone title")
    description: str = Field(..., description="Detailed study instructions or focus areas")
    prerequisites: List[str] = Field(default_factory=list, description="Concepts needed before this step")
    estimated_effort: str = Field("1-2 hours", description="Estimated study time")

    model_config = ConfigDict(from_attributes=True)


class FolderInsightsResponse(BaseModel):
    """AI-synthesized multi-document intelligence across a folder scope."""

    folder_id: UUID
    folder_name: str
    analyzed_documents_count: int
    topic_synthesis: TopicSynthesis
    knowledge_gaps: List[KnowledgeGap]
    learning_roadmap: List[LearningRoadmapItem]

    model_config = ConfigDict(from_attributes=True)


__all__ = [
    "Flashcard",
    "DocumentInsightsResponse",
    "TopicSynthesis",
    "KnowledgeGap",
    "LearningRoadmapItem",
    "FolderInsightsResponse",
]
