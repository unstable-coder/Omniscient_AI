from __future__ import annotations
import json
import shutil
from pathlib import Path
from typing import Any
from app.config import settings

class StorageService:
    def __init__(self) -> None:
        self.upload_dir = settings.UPLOAD_DIR
        self.temp_dir = settings.TEMP_DIR
        self.status_file = settings.STATUS_FILE
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.status_file.parent.mkdir(parents=True, exist_ok=True)

    def save_uploaded_file(self, source_path: Path, target_name: str) -> Path:
        target = self.upload_dir / target_name
        shutil.copy2(source_path, target)
        return target

    def remove_uploaded_file(self, filename: str) -> None:
        target = self.upload_dir / filename
        if target.exists():
            target.unlink()

    def write_json_atomic(self, path: Path, data: Any) -> None:
        temp_path = path.with_suffix(path.suffix + ".tmp")
        with open(temp_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, default=str)
        temp_path.replace(path)

    def read_json(self, path: Path) -> Any:
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
