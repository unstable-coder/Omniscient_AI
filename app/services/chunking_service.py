from __future__ import annotations

import re
from typing import Iterable

from app.config import settings
from app.models.schemas import ContentUnit

WORD_PATTERN = re.compile(r"\S+")


class ChunkingService:
    def __init__(self) -> None:
        self.chunk_size = settings.CHUNK_SIZE
        self.overlap = settings.CHUNK_OVERLAP
        if self.chunk_size <= 0:
            raise ValueError("CHUNK_SIZE must be greater than 0.")

        if self.overlap < 0:
            raise ValueError("CHUNK_OVERLAP cannot be negative.")

        if self.overlap >= self.chunk_size:
            raise ValueError(
                f"Invalid configuration: "
                f"CHUNK_OVERLAP ({self.overlap}) "
                f"must be smaller than "
                f"CHUNK_SIZE ({self.chunk_size})"
            )

    def count_tokens(self, text: str) -> int:
        return len(WORD_PATTERN.findall(text))

    def chunk_units(self, units: Iterable[ContentUnit]) -> list[ContentUnit]:

        chunks: list[ContentUnit] = []

        buffer_text = ""
        buffer_meta: dict[str, object] = {}
        buffer_tokens = 0

        unit_count = 0

        def flush():
            nonlocal buffer_text, buffer_meta, buffer_tokens

            if buffer_text.strip():
                chunks.append(
                    ContentUnit(
                        text=buffer_text.strip(),
                        metadata=buffer_meta.copy(),
                    )
                )

            buffer_text = ""
            buffer_meta = {}
            buffer_tokens = 0

        for unit in units:
            unit_count += 1

            unit_tokens = self.count_tokens(unit.text)

            if unit_tokens == 0:
                print("Skipping empty unit")
                continue

            # Large document
            if unit_tokens >= self.chunk_size:
                if buffer_text:
                    flush()

                large_chunks = self._split_large_unit(unit)

                chunks.extend(large_chunks)
                continue

            if (
                buffer_tokens + unit_tokens > self.chunk_size
                and buffer_text
            ):
                flush()

                buffer_text = unit.text
                buffer_meta = unit.metadata.copy()
                buffer_tokens = unit_tokens

            else:
                if buffer_text:
                    buffer_text += "\n\n"
                else:
                    buffer_meta = unit.metadata.copy()

                buffer_text += unit.text
                buffer_tokens += unit_tokens

        if buffer_text:
            flush()
        chunks = self._add_overlap(chunks)
        return chunks

    def _split_large_unit(
        self,
        unit: ContentUnit,
    ) -> list[ContentUnit]:

        words = WORD_PATTERN.findall(unit.text)
        step = self.chunk_size - self.overlap

        if step <= 0:
            raise ValueError(
                f"Invalid chunk configuration. "
                f"chunk_size={self.chunk_size}, "
                f"overlap={self.overlap}"
            )

        chunks: list[ContentUnit] = []

        iteration = 0

        for start in range(0, len(words), step):

            iteration += 1

            end = min(start + self.chunk_size, len(words))

            chunk_words = words[start:end]

            chunks.append(
                ContentUnit(
                    text=" ".join(chunk_words),
                    metadata=unit.metadata.copy(),
                )
            )
            if end >= len(words):
                break
        return chunks

    def _add_overlap(
        self,
        chunks: list[ContentUnit],
    ) -> list[ContentUnit]:
        if len(chunks) <= 1:
            return chunks

        overlapped: list[ContentUnit] = [chunks[0]]

        for chunk in chunks[1:]:

            previous = overlapped[-1]

            previous_words = WORD_PATTERN.findall(previous.text)
            current_words = WORD_PATTERN.findall(chunk.text)

            overlap_words = current_words[: self.overlap]

            if overlap_words:
                previous_text = (
                    " ".join(previous_words + overlap_words)
                )

                overlapped[-1] = ContentUnit(
                    text=previous_text,
                    metadata=previous.metadata.copy(),
                )

            overlapped.append(chunk)
        return overlapped