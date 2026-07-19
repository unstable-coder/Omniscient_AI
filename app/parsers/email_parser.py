from __future__ import annotations
from typing import Iterable
from email import policy
from email.parser import BytesParser
from app.parsers.base_parser import BaseParser
from app.models.schemas import ContentUnit

class EmailParser(BaseParser):
    supported_extensions = ("eml",)
    supported_mime_types = ("message/rfc822",)

    def parse(self, path: str, metadata: dict[str, object]) -> Iterable[ContentUnit]:
        with open(path, "rb") as handle:
            message = BytesParser(policy=policy.default).parse(handle)
        headers = {k: v for k, v in message.items()}
        body = message.get_body(preferencelist=("plain", "html"))
        text_body = body.get_content().strip() if body else ""
        combined = []
        if headers:
            combined.append("\n".join(f"{k}: {v}" for k, v in headers.items()))
        if text_body:
            combined.append(text_body)
        if combined:
            yield ContentUnit(text="\n\n".join(combined), metadata=metadata)
