from __future__ import annotations

import logging
import re
from collections import defaultdict
from typing import Any

logger = logging.getLogger(__name__)


class EntityResolver:
    """Normalize entity names so equivalent aliases resolve to one canonical entity."""

    def __init__(self) -> None:
        self._aliases: dict[str, str] = {}

    def resolve_entities(self, entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not entities:
            return []

        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for entity in entities:
            key = self._entity_key(entity)
            grouped[key].append(entity)

        resolved: list[dict[str, Any]] = []
        for _, group in grouped.items():
            group = sorted(group, key=lambda item: item.get("confidence", 0.0), reverse=True)
            canonical_name = self._canonical_name(group)
            for entity in group:
                resolved.append(
                    {
                        **entity,
                        "canonical_name": canonical_name,
                        "canonical_key": self._canonical_key(entity, canonical_name),
                    }
                )
        return sorted(resolved, key=lambda item: (item.get("type", ""), item.get("name", "")))

    def _entity_key(self, entity: dict[str, Any]) -> str:
        entity_type = str(entity.get("type", "")).strip()
        return entity_type.lower()

    def _canonical_name(self, entities: list[dict[str, Any]]) -> str:
        if not entities:
            return ""

        for entity in entities:
            name = str(entity.get("name", "")).strip()
            if not name:
                continue
            standardized = self._standardize_asset_name(name)
            if standardized:
                return standardized
        return str(entities[0].get("name", "")).strip()

    def _canonical_key(self, entity: dict[str, Any], canonical_name: str) -> str:
        entity_type = str(entity.get("type", "")).strip()
        return f"{entity_type}:{canonical_name.lower()}"

    @staticmethod
    def _standardize_asset_name(value: str) -> str:
        stripped = str(value).strip()
        if not stripped:
            return ""

        if re.search(r"\b(?:p|pump)\s*[-]?\s*0*(\d+)\b", stripped, flags=re.IGNORECASE):
            match = re.search(r"\b(?:p|pump)\s*[-]?\s*0*(\d+)\b", stripped, flags=re.IGNORECASE)
            if match:
                return f"P{match.group(1)}"

        if re.search(r"\b(?:p|pump)\s*[-]?\s*([a-z])\b", stripped, flags=re.IGNORECASE):
            match = re.search(r"\b(?:p|pump)\s*[-]?\s*([a-z])\b", stripped, flags=re.IGNORECASE)
            if match:
                return f"P{match.group(1).upper()}"

        return stripped
