"""
Document chunking utility for splitting text into semantic chunks with overlap tracking.

Implements hierarchical splitting (paragraph → sentence → word) to preserve semantic boundaries
and configurable token counts for LLM compatibility.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ChunkData:
    """Represents a single text chunk before database insertion."""

    chunk_index: int
    chunk_text: str
    token_count: int
    overlap_tokens: int
    start_character: Optional[int] = None
    end_character: Optional[int] = None


class TextChunker:
    """
    Utility for splitting text into semantically-bounded chunks with configurable overlap.

    Uses hierarchical splitting strategy:
    1. Split by double newlines (paragraphs)
    2. Split by single newlines (sentences/lines)
    3. Split by spaces (words)

    This preserves semantic boundaries and avoids cutting mid-sentence.
    """

    def __init__(
        self,
        target_chunk_tokens: int = 512,
        target_chunk_characters: int = 2000,
        overlap_tokens: int = 50,
        overlap_characters: int = 200,
        tokens_per_character: float = 0.25,
    ):
        """
        Initialize chunker with configurable size parameters.

        Args:
            target_chunk_tokens: Target token count per chunk (default 512).
            target_chunk_characters: Target character count per chunk (default 2000).
            overlap_tokens: Token overlap between adjacent chunks (default 50).
            overlap_characters: Character overlap between adjacent chunks (default 200).
            tokens_per_character: Estimated tokens per character for approximation (default 0.25).
        """
        self.target_chunk_tokens = target_chunk_tokens
        self.target_chunk_characters = target_chunk_characters
        self.overlap_tokens = overlap_tokens
        self.overlap_characters = overlap_characters
        self.tokens_per_character = tokens_per_character

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text using character-based approximation.

        Uses a simple heuristic: tokens ≈ characters * tokens_per_character.
        This provides a fast approximation without requiring a tokenizer library.

        Args:
            text: Text to estimate token count for.

        Returns:
            Estimated token count.
        """
        return max(1, int(len(text.strip()) * self.tokens_per_character))

    def _split_hierarchical(self, text: str) -> List[str]:
        """
        Split text hierarchically to preserve semantic boundaries.

        Strategy:
        1. Split by double newlines (paragraph boundaries)
        2. If segments are too large, split by single newlines (sentence boundaries)
        3. If segments are still too large, split by spaces (word boundaries)
        4. If a single word exceeds limit, include it whole (preserve content)

        Args:
            text: Text to split.

        Returns:
            List of text segments bounded by target size.
        """
        segments: List[str] = []

        # Level 1: Split by paragraph (double newlines)
        paragraphs = text.split("\n\n")

        for paragraph in paragraphs:
            if not paragraph.strip():
                continue

            # Level 2: Split by sentence/line (single newlines)
            lines = paragraph.split("\n")

            for line in lines:
                if not line.strip():
                    continue

                # Check if line fits in target size
                if len(line) <= self.target_chunk_characters:
                    segments.append(line)
                else:
                    # Level 3: Split by spaces (words)
                    words = line.split(" ")
                    current_segment = ""

                    for word in words:
                        test_segment = (
                            current_segment + " " + word
                            if current_segment
                            else word
                        )

                        if len(test_segment) <= self.target_chunk_characters:
                            current_segment = test_segment
                        else:
                            if current_segment:
                                segments.append(current_segment)
                            current_segment = word

                    if current_segment:
                        segments.append(current_segment)

        return segments

    def create_chunks(self, text: str) -> List[ChunkData]:
        """
        Split text into chunks with semantic preservation and overlap tracking.

        Process:
        1. Split text hierarchically to preserve semantic boundaries
        2. Group segments into chunks sized around target_chunk_tokens
        3. Calculate overlap between consecutive chunks
        4. Track character positions and token counts
        5. Return ordered list of ChunkData objects

        Args:
            text: Source text to chunk.

        Returns:
            List of ChunkData objects with indices, text, token counts, and overlap info.
        """
        if not text or not text.strip():
            return []

        # Step 1: Hierarchical splitting
        segments = self._split_hierarchical(text)

        if not segments:
            return []

        chunks: List[ChunkData] = []
        current_chunk_text = ""
        current_chunk_start_char = 0
        original_text_pos = 0
        segment_positions: List[tuple[int, int]] = []

        # Map segments to their positions in original text
        for segment in segments:
            start = text.find(segment, original_text_pos)
            end = start + len(segment)
            segment_positions.append((start, end))
            original_text_pos = end

        # Step 2: Group segments into chunks
        for segment_idx, segment in enumerate(segments):
            segment_text = segment.strip()
            if not segment_text:
                continue

            test_chunk = (
                current_chunk_text + "\n\n" + segment_text
                if current_chunk_text
                else segment_text
            )

            # Check if adding this segment would exceed target size
            test_chunk_tokens = self._estimate_tokens(test_chunk)

            if (
                test_chunk_tokens <= self.target_chunk_tokens
                and len(test_chunk) <= self.target_chunk_characters
            ):
                # Add segment to current chunk
                if current_chunk_text:
                    current_chunk_text += "\n\n" + segment_text
                else:
                    current_chunk_text = segment_text
            else:
                # Segment would overflow; finalize current chunk if not empty
                if current_chunk_text:
                    chunk_tokens = self._estimate_tokens(current_chunk_text)
                    start_char, end_char = segment_positions[segment_idx - 1]

                    chunks.append(
                        ChunkData(
                            chunk_index=len(chunks),
                            chunk_text=current_chunk_text,
                            token_count=chunk_tokens,
                            overlap_tokens=0,
                            start_character=current_chunk_start_char,
                            end_character=end_char,
                        )
                    )

                # Start new chunk with current segment
                current_chunk_text = segment_text
                current_chunk_start_char = segment_positions[segment_idx][0]

        # Step 3: Add final chunk
        if current_chunk_text:
            chunk_tokens = self._estimate_tokens(current_chunk_text)
            if segment_positions:
                start_char, end_char = segment_positions[-1]
            else:
                start_char, end_char = 0, len(text)

            chunks.append(
                ChunkData(
                    chunk_index=len(chunks),
                    chunk_text=current_chunk_text,
                    token_count=chunk_tokens,
                    overlap_tokens=0,
                    start_character=current_chunk_start_char,
                    end_character=end_char,
                )
            )

        # Step 4: Apply overlap between consecutive chunks
        for i in range(1, len(chunks)):
            prev_chunk = chunks[i - 1]
            curr_chunk = chunks[i]

            # Extract overlap from end of previous chunk
            prev_text = prev_chunk.chunk_text
            overlap_char_count = min(
                self.overlap_characters, len(prev_text) // 2
            )

            if overlap_char_count > 0:
                overlap_text = prev_text[-overlap_char_count:]
                calculated_overlap_tokens = self._estimate_tokens(overlap_text)

                # Update current chunk to include overlap at start
                curr_chunk.chunk_text = overlap_text + "\n\n" + curr_chunk.chunk_text
                curr_chunk.overlap_tokens = calculated_overlap_tokens

                # Recalculate token count for current chunk (includes overlap)
                curr_chunk.token_count = self._estimate_tokens(
                    curr_chunk.chunk_text
                )

        return chunks
