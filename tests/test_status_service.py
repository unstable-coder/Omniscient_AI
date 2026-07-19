import tempfile
from pathlib import Path
from app.config import settings
from app.models.schemas import DocumentStatus
from app.services.status_service import StatusService


def test_status_json_write_and_delete(monkeypatch) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir) / "documents.json"
        monkeypatch.setattr(settings, "STATUS_FILE", temp_path)
        service = StatusService()
        document = service.create_new_document("test.txt", "uuid.txt", "txt", "text/plain", 10)
        loaded = service.get_document(document.document_id)
        assert loaded is not None
        assert loaded.original_filename == "test.txt"
        service.delete_document(document.document_id)
        assert service.get_document(document.document_id) is None
