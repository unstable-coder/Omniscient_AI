from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Iterable
from app.models.schemas import ContentUnit

class BaseParser(ABC):
    supported_extensions: tuple[str, ...] = ()
    supported_mime_types: tuple[str, ...] = ()

    @abstractmethod
    def parse(self, path: str, metadata: dict[str, object]) -> Iterable[ContentUnit]:
        raise NotImplementedError
