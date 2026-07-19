from __future__ import annotations
from datetime import datetime
from typing import Any
from pydantic import BaseModel

class ContentUnit(BaseModel):
    text: str
    metadata: dict[str, Any]

class DocumentStatus(BaseModel):
    document_id: str
    original_filename: str
    stored_filename: str
    file_type: str
    mime_type: str
    size: int
    uploaded_at: datetime
    status: str
    chunk_count: int = 0
    error: str = ""
    content_hash: str = ""

class DocumentListResponse(BaseModel):
    documents: list[DocumentStatus]

class GenericResponse(BaseModel):
    status: str
    message: str

class ChatRequest(BaseModel):
    question: str

class ChatSource(BaseModel):
    document_id: str
    chunk_index: int
    original_filename: str
    text: str
    score: float | None = None
    citation: str

class ChatResponse(BaseModel):
    question: str
    answer: str
    sources: list[ChatSource]
    context: str

class ChatHistoryItem(BaseModel):
    id: str
    question: str
    answer: str
    sources: list[ChatSource]
    timestamp: str

class QdrantHealthResponse(BaseModel):
    status: str
    collection: str
    embeddings_dim: int | None = None
    error: str | None = None
