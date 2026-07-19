from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4
from app.models.schemas import DocumentStatus
from app.services.storage_service import StorageService

class StatusService:
    def __init__(self) -> None:
        self.storage = StorageService()
        self.status_file = self.storage.status_file

    def _load(self) -> dict[str, Any]:
        return self.storage.read_json(self.status_file) or {}

    def _save(self, data: dict[str, Any]) -> None:
        self.storage.write_json_atomic(self.status_file, data)

    def create_document(self, document_id: str, record: DocumentStatus) -> None:
        data = self._load()
        data[document_id] = record.model_dump()
        self._save(data)

    def update_document(self, document_id: str, **fields: Any) -> None:
        data = self._load()
        if document_id not in data:
            return
        data[document_id].update(fields)
        self._save(data)

    def delete_document(self, document_id: str) -> None:
        data = self._load()
        if document_id in data:
            del data[document_id]
            self._save(data)

    def list_documents(self) -> list[DocumentStatus]:
        data = self._load()
        return [DocumentStatus(**item) for item in data.values()]

    def get_document(self, document_id: str) -> DocumentStatus | None:
        data = self._load()
        if document_id in data:
            return DocumentStatus(**data[document_id])
        return None

    def create_new_document(self, original_filename: str, stored_filename: str, file_type: str, mime_type: str, size: int, content_hash: str = "") -> DocumentStatus:
        document_id = uuid4().hex
        status = DocumentStatus(
            document_id=document_id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_type=file_type,
            mime_type=mime_type,
            size=size,
            uploaded_at=datetime.utcnow(),
            status="UPLOADED",
        )
        status_payload = status.model_dump()
        if content_hash:
            status_payload["content_hash"] = content_hash
        self.create_document(document_id, DocumentStatus(**status_payload))
        return DocumentStatus(**status_payload)

    def find_document_by_content_hash(self, content_hash: str) -> DocumentStatus | None:
        data = self._load()
        for item in data.values():
            if item.get("content_hash") == content_hash:
                return DocumentStatus(**item)
        return None
