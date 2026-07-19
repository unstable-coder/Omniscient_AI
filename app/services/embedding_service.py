from __future__ import annotations
from typing import Iterable
from sentence_transformers import SentenceTransformer
from app.config import settings

class EmbeddingService:
    def __init__(self) -> None:
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL)

    def embed_texts(self, texts: Iterable[str]) -> list[list[float]]:
        return self.model.encode(list(texts), batch_size=settings.EMBEDDING_BATCH_SIZE, show_progress_bar=False, convert_to_numpy=False)

    def dimension(self) -> int:
        return self.model.get_sentence_embedding_dimension()
