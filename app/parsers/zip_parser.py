from __future__ import annotations
from typing import Iterable
import zipfile
from pathlib import Path
from app.parsers.base_parser import BaseParser
from app.models.schemas import ContentUnit
from app.services.storage_service import StorageService

class ZipParser(BaseParser):
    supported_extensions = ("zip",)
    supported_mime_types = ("application/zip",)

    def parse(self, path: str, metadata: dict[str, object]) -> Iterable[ContentUnit]:
        storage = StorageService()
        with zipfile.ZipFile(path, "r") as archive:
            for member in archive.namelist():
                if member.endswith("/"):
                    continue
                if Path(member).is_absolute() or ".." in Path(member).parts:
                    continue
                target_path = storage.temp_dir / Path(member).name
                with archive.open(member) as source, open(target_path, "wb") as dest:
                    dest.write(source.read())
                from app.parsers.parser_registry import get_parser_for_file
                parser = get_parser_for_file(str(target_path))
                if parser:
                    yield from parser.parse(str(target_path), {**metadata, "archive_inner_path": member})
                target_path.unlink(missing_ok=True)
