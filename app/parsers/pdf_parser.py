from __future__ import annotations
import logging
from typing import Any, Iterable
from app.parsers.base_parser import BaseParser
from app.models.schemas import ContentUnit

logger = logging.getLogger(__name__)

try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except Exception:
    OCR_AVAILABLE = False

class PDFParser(BaseParser):
    supported_extensions = ("pdf",)
    supported_mime_types = ("application/pdf",)

    def parse(self, path: str, metadata: dict[str, object]) -> Iterable[ContentUnit]:
        try:
            import pdfplumber
        except Exception as exc:
            logger.warning("pdfplumber unavailable: %s", exc)
            return

        with pdfplumber.open(path) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                if not text.strip() and OCR_AVAILABLE:
                    text = self._extract_ocr_text(page)
                if not text.strip():
                    continue
                unit_metadata = {**metadata, "page_number": page_number}
                yield ContentUnit(text=text.strip(), metadata=unit_metadata)

    def _extract_ocr_text(self, page: Any) -> str:
        try:
            page_image = page.to_image(resolution=300)
            image = getattr(page_image, "original", None)
            if image is None:
                return ""
            return pytesseract.image_to_string(image).strip()
        except Exception:
            return ""
