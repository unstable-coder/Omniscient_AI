from __future__ import annotations
from typing import Iterable
from app.parsers.base_parser import BaseParser
from app.models.schemas import ContentUnit

class TextParser(BaseParser):
    supported_extensions = ("txt", "md", "rst", "log", "cfg", "ini", "yaml", "yml", "json", "xml", "html", "csv", "tsv")
    supported_mime_types = (
        "text/plain",
        "text/markdown",
        "application/json",
        "application/xml",
        "text/html",
        "text/csv",
        "text/tab-separated-values",
        "application/x-yaml",
    )

    def parse(self, path: str, metadata: dict[str, object]) -> Iterable[ContentUnit]:
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            text = handle.read().strip()
            if text:
                yield ContentUnit(text=text, metadata=metadata)
