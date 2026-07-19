from __future__ import annotations

import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4, uuid5, NAMESPACE_URL

from fastapi import UploadFile

from app.config import settings
from app.models.schemas import ContentUnit, DocumentStatus
from app.parsers.parser_registry import get_parser_for_file, get_mime_type
from app.services.chunking_service import ChunkingService
from app.services.embedding_service import EmbeddingService
from app.services.entity_extractor import EntityExtractor
from app.services.entity_resolver import EntityResolver
from app.services.neo4j_loader import Neo4jLoader
from app.services.qdrant_service import QdrantService
from app.services.status_service import StatusService
from app.services.storage_service import StorageService
from app.utils.file_utils import sanitize_filename

logger = logging.getLogger(__name__)


class IngestionService:
    def __init__(self) -> None:
        self.storage = StorageService()
        self.status_service = StatusService()
        self.chunking = ChunkingService()
        self.embedding_service = EmbeddingService()
        self.qdrant = QdrantService(
            vector_size=self.embedding_service.dimension()
        )
        self.entity_extractor = EntityExtractor()
        self.entity_resolver = EntityResolver()
        self.neo4j_loader = Neo4jLoader(
            uri=settings.NEO4J_URI,
            user=settings.NEO4J_USER,
            password=settings.NEO4J_PASSWORD,
        )
        self.executor = ThreadPoolExecutor(max_workers=2)

    def save_upload(
        self,
        upload: UploadFile
    ) -> tuple[Path, str, str, str, int, str]:
        original_name = sanitize_filename(
            upload.filename or "uploaded_file"
        )

        ext = Path(original_name).suffix
        safe_name = f"{uuid4().hex}{ext}"
        target_path = self.storage.upload_dir / safe_name

        content = upload.file.read()
        content_hash = hashlib.sha256(content).hexdigest()

        if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise ValueError(
                "File size exceeds maximum upload size."
            )

        with open(target_path, "wb") as handle:
            handle.write(content)

        mime_type = get_mime_type(str(target_path))

        return (
            target_path,
            original_name,
            safe_name,
            mime_type,
            target_path.stat().st_size,
            content_hash,
        )

    def submit_background(
        self,
        document_id: str,
        file_path: Path,
        status_record: DocumentStatus,
    ) -> None:
        self.executor.submit(
            self._process_document,
            document_id,
            file_path,
            status_record,
        )

    def _process_document(
        self,
        document_id: str,
        file_path: Path,
        status_record: DocumentStatus,
    ) -> None:
        self.status_service.update_document(
            document_id,
            status="PROCESSING",
            error="",
        )

        try:
            content_hash = self._compute_content_hash(file_path)
            if self._is_duplicate_upload(content_hash, document_id):
                logger.info(
                    "Skipping duplicate upload for document %s with hash %s",
                    document_id,
                    content_hash,
                )
                self.status_service.update_document(
                    document_id,
                    status="SKIPPED",
                    error="Duplicate content already processed.",
                )
                return

            parser = get_parser_for_file(str(file_path))

            if parser is None:
                self.status_service.update_document(
                    document_id,
                    status="UNSUPPORTED",
                    error="Unsupported file type.",
                )
                return

            units = list(
                parser.parse(
                    str(file_path),
                    {
                        "original_filename":
                            status_record.original_filename
                    },
                )
            )

            if not units:
                self.status_service.update_document(
                    document_id,
                    status="FAILED",
                    error="No extractable content found.",
                )
                return

            chunks = self.chunking.chunk_units(units)

            embedding_result, graph_entities = self._run_parallel_processing(
                document_id,
                status_record,
                chunks,
            )

            self.qdrant.upsert_vectors(embedding_result)
            self._ingest_graph(document_id, graph_entities)

            self.status_service.update_document(
                document_id,
                status="INDEXED",
                chunk_count=len(chunks),
                error="",
            )

        except Exception as exc:
            self.status_service.update_document(
                document_id,
                status="FAILED",
                error=str(exc),
            )

    def _run_parallel_processing(
        self,
        document_id: str,
        status_record: DocumentStatus,
        chunks: list[ContentUnit],
    ) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
        embedding_future = self.executor.submit(
            self._build_payloads,
            document_id,
            status_record,
            chunks,
        )
        entity_future = self.executor.submit(
            self._extract_entities,
            document_id,
            chunks,
        )

        try:
            payloads = embedding_future.result()
            entities = entity_future.result()
        except Exception as exc:
            logger.exception("Parallel ingestion failed for document %s: %s", document_id, exc)
            raise

        return payloads, entities

    def _build_payloads(
        self,
        document_id: str,
        status_record: DocumentStatus,
        chunks: list[ContentUnit],
    ) -> list[dict[str, object]]:
        payloads = []

        # Embed all chunks in one batch instead of one model call per chunk.
        texts = [chunk.text for chunk in chunks]
        vectors = self.embedding_service.embed_texts(texts)

        for index, (chunk, vector) in enumerate(
            zip(chunks, vectors),
            start=1,
        ):
            # Deterministic valid Qdrant UUID point ID.
            chunk_id = str(
                uuid5(
                    NAMESPACE_URL,
                    f"{document_id}:{index}",
                )
            )

            payloads.append(
                {
                    "id": chunk_id,
                    "vector": vector,
                    "payload": {
                        "document_id": document_id,
                        "chunk_id": chunk_id,
                        "chunk_index": index,
                        "text": chunk.text,
                        "original_filename":
                            status_record.original_filename,
                        "stored_filename":
                            status_record.stored_filename,
                        "file_type":
                            status_record.file_type,
                        "mime_type":
                            status_record.mime_type,
                        "source_metadata":
                            chunk.metadata,
                        "uploaded_at":
                            status_record.uploaded_at.isoformat(),
                    },
                }
            )

        return payloads

    def _extract_entities(
        self,
        document_id: str,
        chunks: list[ContentUnit],
    ) -> list[dict[str, object]]:
        extracted_entities: list[dict[str, object]] = []

        for index, chunk in enumerate(chunks, start=1):
            try:
                chunk_entities = self.entity_extractor.extract_entities(
                    text=chunk.text,
                    document_id=document_id,
                    chunk_id=f"{document_id}:{index}",
                    chunk_index=index,
                )
                if chunk_entities:
                    resolved = self.entity_resolver.resolve_entities(chunk_entities)
                    extracted_entities.extend(resolved)
            except Exception as exc:
                logger.exception(
                    "Entity extraction failed for document %s chunk %s: %s",
                    document_id,
                    index,
                    exc,
                )

        return extracted_entities

    def _compute_content_hash(self, file_path: Path) -> str:
        sha256 = hashlib.sha256()
        with file_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _is_duplicate_upload(self, content_hash: str, document_id: str) -> bool:
        existing_document = self.status_service.find_document_by_content_hash(content_hash)
        if existing_document is None:
            return False
        if existing_document.document_id == document_id:
            return False
        logger.info(
            "Found existing document %s with same content hash %s",
            existing_document.document_id,
            content_hash,
        )
        return True

    def _ingest_graph(
        self,
        document_id: str,
        entities: list[dict[str, object]],
    ) -> None:
        if not entities:
            logger.info("No graph entities to persist for document %s", document_id)
            return

        normalized_entities = [
            {
                **entity,
                "source_document": entity.get("source_document", document_id),
            }
            for entity in entities
        ]

        try:
            self.neo4j_loader.persist(normalized_entities)
        except Exception as exc:  # pragma: no cover - defensive path
            logger.exception(
                "Neo4j ingestion failed for document %s: %s",
                document_id,
                exc,
            )

    def remove_document(
        self,
        document_id: str,
        stored_filename: str,
    ) -> None:
        self.storage.remove_uploaded_file(stored_filename)
        self.qdrant.delete_by_document_id(document_id)
        self.status_service.delete_document(document_id)