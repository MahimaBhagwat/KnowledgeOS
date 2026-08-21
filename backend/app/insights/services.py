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
