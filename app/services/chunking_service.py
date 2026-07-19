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

    def chunk_units(self, units: Iterable[ContentUnit]) -> list[ContentUnit]:
        chunks: list[ContentUnit] = []
        buffer_text = ""
        buffer_meta: dict[str, object] = {}
        buffer_tokens = 0

        def flush():
            nonlocal buffer_text, buffer_meta, buffer_tokens
            if buffer_text.strip():
                chunks.append(ContentUnit(text=buffer_text.strip(), metadata=buffer_meta.copy()))
            buffer_text = ""
            buffer_meta = {}
            buffer_tokens = 0

        def count_tokens(text: str) -> int:
            return len(WORD_PATTERN.findall(text))

        for unit in units:
            unit_tokens = count_tokens(unit.text)
            if unit_tokens >= self.chunk_size:
                if buffer_text:
                    flush()
                chunks.extend(self._split_large_unit(unit))
                continue
            if buffer_tokens + unit_tokens > self.chunk_size and buffer_text:
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

        return self._add_overlap(chunks)

    def _split_large_unit(self, unit: ContentUnit) -> list[ContentUnit]:
        words = WORD_PATTERN.findall(unit.text)
        chunks = []
        start = 0
        while start < len(words):
            end = min(start + self.chunk_size, len(words))
            chunk_text = " ".join(words[start:end])
            chunks.append(ContentUnit(text=chunk_text, metadata=unit.metadata.copy()))
            start = end - self.overlap
            if start < 0:
                start = 0
            if start >= len(words):
                break
        return chunks

    def _add_overlap(self, chunks: list[ContentUnit]) -> list[ContentUnit]:
        overlapped: list[ContentUnit] = []
        for index, chunk in enumerate(chunks):
            if index == 0:
                overlapped.append(chunk)
                continue
            prev = overlapped[-1]
            prev_words = WORD_PATTERN.findall(prev.text)
            current_words = WORD_PATTERN.findall(chunk.text)
            overlap_text = " ".join(current_words[: self.overlap])
            if overlap_text:
                text = " ".join(prev_words + [overlap_text]).strip()
                overlapped[-1] = ContentUnit(text=text, metadata=prev.metadata.copy())
            overlapped.append(chunk)
        return overlapped
