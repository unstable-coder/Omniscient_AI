from __future__ import annotations
from typing import Iterable
from pathlib import Path
from app.parsers.base_parser import BaseParser
from app.models.schemas import ContentUnit

try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except Exception:
    OCR_AVAILABLE = False

class ImageParser(BaseParser):
    supported_extensions = ("png", "jpg", "jpeg", "tiff", "bmp", "webp")
    supported_mime_types = (
        "image/png",
        "image/jpeg",
        "image/tiff",
        "image/bmp",
        "image/webp",
    )

    def parse(self, path: str, metadata: dict[str, object]) -> Iterable[ContentUnit]:
        if not OCR_AVAILABLE:
            return
        text = self._extract_text(path)
        if text:
            yield ContentUnit(text=text, metadata=metadata)

    def _extract_text(self, path: str) -> str:
        try:
            with Image.open(path) as image:
                return pytesseract.image_to_string(image).strip()
        except Exception:
            return ""
