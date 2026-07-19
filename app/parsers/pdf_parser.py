from __future__ import annotations
from typing import Iterable
import fitz
import pdfplumber
from app.parsers.base_parser import BaseParser
from app.models.schemas import ContentUnit

class PDFParser(BaseParser):
    supported_extensions = ("pdf",)
    supported_mime_types = ("application/pdf",)

    def parse(self, path: str, metadata: dict[str, object]) -> Iterable[ContentUnit]:
        with pdfplumber.open(path) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                if not text.strip():
                    continue
                unit_metadata = {**metadata, "page_number": page_number}
                yield ContentUnit(text=text.strip(), metadata=unit_metadata)
