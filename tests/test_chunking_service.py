from app.models.schemas import ContentUnit
from app.services.chunking_service import ChunkingService


def test_chunking_preserves_metadata() -> None:
    units = [
        ContentUnit(text="First paragraph about pump 123.", metadata={"page_number": 1}),
        ContentUnit(text="Second paragraph about motor units and equipment.", metadata={"page_number": 1}),
    ]
    chunker = ChunkingService()
    chunker.chunk_size = 10
    chunker.overlap = 2
    chunks = chunker.chunk_units(units)
    assert len(chunks) >= 1
    for chunk in chunks:
        assert "page_number" in chunk.metadata
