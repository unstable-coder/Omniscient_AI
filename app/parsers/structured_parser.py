from __future__ import annotations
from typing import Iterable
import json
import yaml
from bs4 import BeautifulSoup
from defusedxml.ElementTree import parse as safe_parse
from app.parsers.base_parser import BaseParser
from app.models.schemas import ContentUnit

class StructuredParser(BaseParser):
    supported_extensions = ("json", "xml", "html", "yaml", "yml")
    supported_mime_types = (
        "application/json",
        "application/xml",
        "text/xml",
        "text/html",
        "application/x-yaml",
        "text/yaml",
    )

    def parse(self, path: str, metadata: dict[str, object]) -> Iterable[ContentUnit]:
        suffix = path.rsplit('.', 1)[-1].lower()
        if suffix == "json":
            yield from self._parse_json(path, metadata)
        elif suffix == "xml":
            yield from self._parse_xml(path, metadata)
        elif suffix == "html":
            yield from self._parse_html(path, metadata)
        elif suffix in ("yaml", "yml"):
            yield from self._parse_yaml(path, metadata)

    def _parse_json(self, path: str, metadata: dict[str, object]) -> Iterable[ContentUnit]:
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            data = json.load(handle)
        yield from self._walk_json(data, metadata, [])

    def _walk_json(self, fragment: object, metadata: dict[str, object], path: list[str]) -> Iterable[ContentUnit]:
        if isinstance(fragment, dict):
            for key, value in fragment.items():
                yield from self._walk_json(value, metadata, path + [str(key)])
        elif isinstance(fragment, list):
            for index, item in enumerate(fragment):
                yield from self._walk_json(item, metadata, path + [str(index)])
        else:
            text = str(fragment).strip()
            if text:
                yield ContentUnit(text=text, metadata={**metadata, "json_path": ".".join(path)})

    def _parse_xml(self, path: str, metadata: dict[str, object]) -> Iterable[ContentUnit]:
        tree = safe_parse(path)
        root = tree.getroot()
        for element in root.iter():
            if element.text and element.text.strip():
                yield ContentUnit(text=element.text.strip(), metadata={**metadata, "xml_tag": element.tag})

    def _parse_html(self, path: str, metadata: dict[str, object]) -> Iterable[ContentUnit]:
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            soup = BeautifulSoup(handle, "html.parser")
        for script in soup(["script", "style"]):
            script.decompose()
        text = "\n".join(line.strip() for line in soup.stripped_strings if line.strip())
        if text:
            yield ContentUnit(text=text, metadata={**metadata, "html_source": path})

    def _parse_yaml(self, path: str, metadata: dict[str, object]) -> Iterable[ContentUnit]:
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            data = yaml.safe_load(handle)
        if data is None:
            return
        yield from self._walk_json(data, metadata, [])
