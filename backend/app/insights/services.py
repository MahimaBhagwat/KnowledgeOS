from __future__ import annotations

import json

from typing import Any, Dict, List, Optional
from uuid import UUID

import litellm
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

try:
    from app.ingestion.repositories import DocumentChunkRepository  # type: ignore
except Exception:  # pragma: no cover - repository may not exist during incremental implementation
    DocumentChunkRepository = None  # type: ignore


class InsightService:
    """Generate quick AI-driven insights for a document.

    This service uses existing chunk data to synthesize a short executive
    summary, key takeaways, and flashcards. The implementation uses simple
    heuristics and text transformations as a deterministic placeholder for a
    future LLM-based summarizer.
    """

    @staticmethod
    async def generate_document_insights(session: AsyncSession, profile_id: UUID, document_id: UUID) -> Dict[str, Any]:
        if DocumentChunkRepository is None:
            raise RuntimeError("DocumentChunkRepository is not available in this build. Implement app.ingestion.repositories.DocumentChunkRepository before using InsightService.")

        chunks = await DocumentChunkRepository.get_chunks_by_document(session=session, document_id=document_id, profile_id=profile_id)
        if not chunks:
            return {
                "document_id": str(document_id),
                "summary": "",
                "key_takeaways": [],
                "flashcards": [],
            }

        # Build a naive summary: take the first 2 non-empty chunks joined
        non_empty_texts = [c.chunk_text.strip() for c in chunks if c.chunk_text and c.chunk_text.strip()]
        full_text = "\n\n".join(non_empty_texts)

        parsed = await InsightService._call_llm(full_text)

        # # Key takeaways: extract short leading sentences from first few chunks
        # takeaways: List[str] = []
        # for text in non_empty_texts[:4]:
        #     sentence = text.split(".\n")[0].split(".")[0].strip()
        #     if sentence:
        #         takeaways.append(sentence if len(sentence) <= 200 else sentence[:197] + "...")

        # # Flashcards: produce simple Q/A pairs from headings or leading lines
        # flashcards: List[Dict[str, str]] = []
        # for idx, text in enumerate(non_empty_texts[:4], start=1):
        #     first_line = text.splitlines()[0].strip() if text.splitlines() else text.strip()
        #     question = f"What is the main idea of section {idx}?"
        #     answer = first_line if len(first_line) <= 240 else first_line[:237] + "..."
        #     flashcards.append({"question": question, "answer": answer})

        return {
            "document_id": str(document_id),
            "summary": parsed.get("summary", ""),
            "key_takeaways": parsed.get("key_takeaways", []),
            "flashcards": parsed.get("flashcards", []),
        }

    @staticmethod
    async def generate_folder_insights(session: AsyncSession, profile_id: UUID, folder_id: UUID) -> Dict[str, Any]:
        """Synthesize multi-document insights across all documents in a folder."""
        from app.folders.repositories import FolderRepository
        from app.documents.repositories import DocumentRepository

        folder = await FolderRepository.get_by_id(session=session, folder_id=folder_id, profile_id=profile_id)
        if not folder:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")

        documents = await DocumentRepository.get_user_documents(session=session, profile_id=profile_id, folder_id=folder_id)
        if not documents:
            return {
                "folder_id": str(folder_id),
                "folder_name": folder.name,
                "analyzed_documents_count": 0,
                "topic_synthesis": {
                    "title": f"Empty Folder: {folder.name}",
                    "overview": "No documents found in this folder to analyze.",
                    "connected_themes": [],
                    "key_concepts": [],
                },
                "knowledge_gaps": [],
                "learning_roadmap": [],
            }

        doc_sections: List[str] = []
        for doc in documents:
            if DocumentChunkRepository is not None:
                chunks = await DocumentChunkRepository.get_chunks_by_document(
                    session=session,
                    document_id=doc.id,
                    profile_id=profile_id,
                )
                chunk_texts = [c.chunk_text.strip() for c in chunks if c.chunk_text and c.chunk_text.strip()]
                joined = "\n\n".join(chunk_texts[:10])  # limit per document for token budget
                doc_title = getattr(doc, "name", getattr(doc, "title", "Document"))
                if joined:
                    doc_sections.append(f"### Document: {doc_title}\n{joined}")

        if not doc_sections:
            return {
                "folder_id": str(folder_id),
                "folder_name": folder.name,
                "analyzed_documents_count": len(documents),
                "topic_synthesis": {
                    "title": folder.name,
                    "overview": "Documents in this folder contain no processed text chunks yet.",
                    "connected_themes": [],
                    "key_concepts": [],
                },
                "knowledge_gaps": [],
                "learning_roadmap": [],
            }

        full_corpus = "\n\n---\n\n".join(doc_sections)
        parsed = await InsightService._call_folder_llm(folder.name, full_corpus)

        return {
            "folder_id": str(folder_id),
            "folder_name": folder.name,
            "analyzed_documents_count": len(documents),
            "topic_synthesis": parsed.get("topic_synthesis", {
                "title": folder.name,
                "overview": "Topic synthesis completed.",
                "connected_themes": [],
                "key_concepts": [],
            }),
            "knowledge_gaps": parsed.get("knowledge_gaps", []),
            "learning_roadmap": parsed.get("learning_roadmap", []),
        }

    @staticmethod
    async def _call_folder_llm(folder_name: str, full_text: str) -> Dict[str, Any]:
        """Call LiteLLM for multi-document synthesis, knowledge gap identification, and roadmap creation."""
        prompt = (
            f"You are an expert AI tutor analyzing a collection of documents in folder '{folder_name}'.\n"
            "Synthesize the documents into a cohesive multi-document intelligence report.\n\n"
            "Return ONLY valid JSON (no markdown fences, no preamble) with this exact JSON structure:\n"
            "{\n"
            '  "topic_synthesis": {\n'
            '    "title": "Synthesized Topic Title",\n'
            '    "overview": "3-5 sentence synthesis connecting ideas across the documents",\n'
            '    "connected_themes": ["Theme 1", "Theme 2", "Theme 3"],\n'
            '    "key_concepts": ["Concept A", "Concept B", "Concept C", "Concept D"]\n'
            "  },\n"
            '  "knowledge_gaps": [\n'
            "    {\n"
            '      "topic": "Missing or shallow topic",\n'
            '      "description": "Why this represents a gap or prerequisite not fully covered",\n'
            '      "recommendation": "What to read or study to close this gap",\n'
            '      "severity": "medium"\n'
            "    }\n"
            "  ],\n"
            '  "learning_roadmap": [\n'
            "    {\n"
            '      "step": 1,\n'
            '      "title": "Foundation & Prerequisites",\n'
            '      "description": "What to focus on first",\n'
            '      "prerequisites": ["Prereq 1"],\n'
            '      "estimated_effort": "2 hours"\n'
            "    },\n"
            "    {\n"
            '      "step": 2,\n'
            '      "title": "Core Deep Dive",\n'
            '      "description": "Deep understanding of main concepts",\n'
            '      "prerequisites": ["Step 1 completion"],\n'
            '      "estimated_effort": "3 hours"\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            f"Document Corpus:\n{full_text}"
        )

        try:
            response = await litellm.acompletion(
                model=settings.llm_chat_model_name,
                messages=[{"role": "user", "content": prompt}],
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

        raw = str(content).strip()
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"LLM returned invalid JSON: {str(exc)}") from exc

        return parsed

    @staticmethod
    async def _call_llm(full_text: str) -> Dict[str, Any]:
        """Call the configured LiteLLM provider and return parsed structured insights."""
        prompt = (
            "You will read study notes and produce structured learning aids.\n\n"
            "Return ONLY valid JSON, no markdown fences, no preamble, in exactly this shape:\n"
            '{"summary": "a concise 3-5 sentence executive summary", '
            '"key_takeaways": ["takeaway 1", "takeaway 2"], '
            '"flashcards": [{"question": "...", "answer": "..."}]}\n\n'
            "Produce 4-6 key_takeaways and 5-8 flashcards that test real understanding "
            "of the material (not just \"what is section X about\").\n\n"
            f"Notes:\n{full_text}"
        )

        try:
            response = await litellm.acompletion(
                model=settings.llm_chat_model_name,
                messages=[{"role": "user", "content": prompt}],
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

        raw = str(content).strip()
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"LLM returned invalid JSON: {str(exc)}") from exc

        return parsed


__all__ = ["InsightService"]
