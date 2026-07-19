from __future__ import annotations
from fastapi import APIRouter, BackgroundTasks, File, UploadFile, HTTPException
from app.models.schemas import DocumentListResponse, DocumentStatus, GenericResponse, QdrantHealthResponse
from app.services.ingestion_service import IngestionService
from app.services.status_service import StatusService
from app.services.storage_service import StorageService

router = APIRouter()
service = IngestionService()
status_service = StatusService()
storage = StorageService()

@router.get("/health", response_model=GenericResponse)
def health() -> GenericResponse:
    return GenericResponse(status="ok", message="service is running")

@router.get("/qdrant-health", response_model=QdrantHealthResponse)
def qdrant_health() -> QdrantHealthResponse:
    result = service.qdrant.health()
    return QdrantHealthResponse(status=result.get("status", "error"), collection=result.get("collection", ""), embeddings_dim=result.get("embedding_dim"), error=result.get("error"))

@router.post("/documents/upload", response_model=GenericResponse)
def upload_documents(background_tasks: BackgroundTasks, files: list[UploadFile] = File(...)) -> GenericResponse:
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    for upload in files:
        file_path, original_name, safe_name, mime_type, size, content_hash = service.save_upload(upload)
        document = status_service.create_new_document(
            original_name,
            safe_name,
            upload.content_type or mime_type,
            mime_type,
            size,
            content_hash=content_hash,
        )
        background_tasks.add_task(service.submit_background, document.document_id, file_path, document)
    return GenericResponse(status="ok", message="Files uploaded successfully")

@router.get("/documents", response_model=DocumentListResponse)
def list_documents() -> DocumentListResponse:
    documents = status_service.list_documents()
    return DocumentListResponse(documents=documents)

@router.get("/documents/{document_id}", response_model=DocumentStatus)
def get_document(document_id: str) -> DocumentStatus:
    document = status_service.get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document

@router.post("/documents/{document_id}/retry", response_model=GenericResponse)
def retry_document(document_id: str) -> GenericResponse:
    document = status_service.get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    file_path = storage.upload_dir / document.stored_filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Stored file not found")
    status_service.update_document(document_id, status="UPLOADED", error="")
    service.submit_background(document_id, file_path, document)
    return GenericResponse(status="ok", message="Retry initiated")

@router.delete("/documents/{document_id}", response_model=GenericResponse)
def delete_document(document_id: str) -> GenericResponse:
    document = status_service.get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    service.remove_document(document_id, document.stored_filename)
    return GenericResponse(status="ok", message="Document deleted")
