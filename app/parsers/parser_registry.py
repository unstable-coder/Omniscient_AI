from __future__ import annotations
import mimetypes
from pathlib import Path
from typing import Iterable
from app.parsers.base_parser import BaseParser
from app.parsers.pdf_parser import PDFParser
from app.parsers.document_parser import DocumentParser
from app.parsers.text_parser import TextParser
from app.parsers.tabular_parser import TabularParser
from app.parsers.structured_parser import StructuredParser
from app.parsers.image_parser import ImageParser
from app.parsers.email_parser import EmailParser

PARSER_CLASSES: list[type[BaseParser]] = [
    PDFParser,
    DocumentParser,
    TabularParser,
    StructuredParser,
    TextParser,
    ImageParser,
    EmailParser,
]

def get_parser_for_file(path: str) -> BaseParser | None:
    from app.parsers.zip_parser import ZipParser

    file_path = Path(path)
    ext = file_path.suffix.lower().lstrip('.')
    mime_type, _ = mimetypes.guess_type(path)
    for parser_cls in PARSER_CLASSES + [ZipParser]:
        if ext in parser_cls.supported_extensions:
            return parser_cls()
        if mime_type and mime_type in parser_cls.supported_mime_types:
            return parser_cls()
    return None

def get_mime_type(path: str) -> str:
    mime_type, _ = mimetypes.guess_type(path)
    return mime_type or "application/octet-stream"
