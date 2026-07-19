from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
import uuid

from app.config import settings
from app.services.storage_service import StorageService
from app.models.schemas import ChatHistoryItem, ChatSource
class HistoryService:
    def __init__(self) -> None:
        self.storage = StorageService()
        self.history_file: Path = settings.HISTORY_FILE
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

    def read_history(self) -> list[ChatHistoryItem]:
        raw = self.storage.read_json(self.history_file) or []
        return [ChatHistoryItem(**item) for item in raw]

    def save_entry(self, question: str, answer: str, sources: list[ChatSource]) -> None:
        history = self.read_history()
        entry = ChatHistoryItem(
            id=str(uuid.uuid4()),
            question=question,
            answer=answer,
            sources=sources,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        history.insert(0, entry)
        self.storage.write_json_atomic(
            self.history_file,
            [item.dict() for item in history[:50]],
        )

    def clear_history(self) -> None:
        self.storage.write_json_atomic(self.history_file, [])
