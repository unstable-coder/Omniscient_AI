from __future__ import annotations
from typing import Any
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from app.config import settings
from qdrant_client.http import models as rest

class QdrantService:
    def __init__(self, vector_size: int) -> None:
        self.client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)
        self.collection_name = settings.QDRANT_COLLECTION
        self.vector_size = vector_size
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        collections = self.client.get_collections().collections
        if self.collection_name not in [collection.name for collection in collections]:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=rest.VectorParams(size=self.vector_size, distance=rest.Distance.COSINE),
            )
            return
        collection_info = self.client.get_collection(collection_name=self.collection_name)
        vectors_config = collection_info.config.params.vectors
        if hasattr(vectors_config, "size"):
            existing_size = vectors_config.size

            if existing_size != self.vector_size:
                raise RuntimeError(
                    f"Qdrant collection '{settings.QDRANT_COLLECTION}' "
                    f"has vector size {existing_size}, "
                    f"but embedding model requires {self.vector_size}."
                )

    def upsert_vectors(self, vectors: list[dict[str, Any]]) -> None:
        points = [
            rest.PointStruct(id=item["id"], vector=item["vector"], payload=item["payload"])
            for item in vectors
        ]
        self.client.upsert(collection_name=self.collection_name, points=points)

    def query_vectors(self, vector: list[float], limit: int = 5, filter: dict[str, Any] | None = None) -> list[rest.ScoredPoint]:
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=vector,
            limit=limit,
            with_payload=True,
            with_vectors=False,
            query_filter=filter,
        )
        return getattr(response, "points", [])


    def delete_by_document_id(self, document_id: str) -> None:
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=rest.Filter(
                must=[
                    rest.FieldCondition(
                        key="document_id",
                        match=rest.MatchValue(value=document_id),
                    )
                ]
            ),
        )
    def health(self) -> dict[str, Any]:
        try:
            collection_info = self.client.get_collection(collection_name=self.collection_name)
            return {"status": "ok", "collection": self.collection_name, "embedding_dim": collection_info.vectors.size if collection_info.vectors else None}
        except Exception as exc:
            return {"status": "error", "collection": self.collection_name, "embedding_dim": None, "error": str(exc)}
