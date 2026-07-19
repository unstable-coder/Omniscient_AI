from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

ALLOWED_ENTITY_TYPES = {
    "Asset",
    "Component",
    "Symptom",
    "FailureMode",
    "Action",
    "Inspection",
    "Incident",
    "WorkOrder",
    "EquipmentModel",
    "Location",
}


class EntityExtractor:
    """Extract structured entities from a chunk using an LLM when available."""

    def __init__(self, model: str | None = None, api_key: str | None = None) -> None:
        self.model = model or settings.GEMINI_MODEL
        self.api_key = api_key or settings.GOOGLE_API_KEY
        self._llm: Any | None = None
        self._initialize_llm()

    def _initialize_llm(self) -> None:
        if not self.api_key:
            return

        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except Exception as exc:  # pragma: no cover - defensive path
            logger.warning("Google Generative AI client is unavailable: %s", exc)
            return

        try:
            self._llm = ChatGoogleGenerativeAI(
                model=self.model,
                google_api_key=self.api_key,
                temperature=0,
            )
        except Exception as exc:  # pragma: no cover - defensive path
            logger.warning("Unable to initialize Gemini client: %s", exc)
            self._llm = None

    def extract_entities(
        self,
        text: str,
        document_id: str,
        chunk_id: str,
        chunk_index: int,
    ) -> list[dict[str, Any]]:
        if not text or not text.strip():
            return []

        try:
            if self._llm is not None:
                return self._extract_with_llm(text, document_id, chunk_id, chunk_index)
        except Exception as exc:  # pragma: no cover - defensive path
            logger.warning("LLM extraction failed, falling back to heuristic parser: %s", exc)

        return self._extract_with_fallback(text, document_id, chunk_id, chunk_index)

    def _extract_with_llm(
        self,
        text: str,
        document_id: str,
        chunk_id: str,
        chunk_index: int,
    ) -> list[dict[str, Any]]:
        from langchain_core.messages import HumanMessage

        prompt = (
            "You are extracting industrial maintenance entities from text. "
            "Return only valid JSON. "
            "The output must be a JSON array of objects with the keys: "
            "type, name, confidence, evidence. "
            f"Allowed types: {sorted(ALLOWED_ENTITY_TYPES)}. "
            "Do not include any explanation or markdown.\n\n"
            f"Text:\n{text}"
        )
        response = self._llm.invoke([HumanMessage(content=prompt)])
        content = self._normalize_llm_content(response)
        payload = self._parse_json_payload(content)

        if isinstance(payload, dict):
            payload = [payload]
        if not isinstance(payload, list):
            return []

        entities: list[dict[str, Any]] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            entity_type = str(item.get("type", "")).strip()
            if entity_type not in ALLOWED_ENTITY_TYPES:
                continue
            name = str(item.get("name", "")).strip()
            evidence = str(item.get("evidence", text)).strip() or text.strip()
            confidence = float(item.get("confidence", 0.75) or 0.75)
            if not name:
                continue
            entities.append(
                {
                    "type": entity_type,
                    "name": name,
                    "confidence": max(0.0, min(1.0, confidence)),
                    "evidence": evidence,
                    "source_document": document_id,
                    "chunk_id": chunk_id,
                    "chunk_index": chunk_index,
                }
            )
        return entities

    def _extract_with_fallback(
        self,
        text: str,
        document_id: str,
        chunk_id: str,
        chunk_index: int,
    ) -> list[dict[str, Any]]:
        entities: list[dict[str, Any]] = []
        lowered = text.lower()

        asset_patterns = [
            r"\b(?:pump|compressor|motor|fan|boiler|valve|tank|cooler|chiller|generator|conveyor)\b",
            r"\b[a-z0-9-]+(?:pump|compressor|motor|fan|boiler|valve|tank|cooler|chiller|generator|conveyor)\b",
        ]
        for pattern in asset_patterns:
            matches = re.findall(pattern, text, flags=re.IGNORECASE)
            if matches:
                asset_name = matches[0]
                entities.append(
                    {
                        "type": "Asset",
                        "name": asset_name.strip(),
                        "confidence": 0.7,
                        "evidence": text.strip(),
                        "source_document": document_id,
                        "chunk_id": chunk_id,
                        "chunk_index": chunk_index,
                    }
                )
                break

        if re.search(r"\b(?:seal|bearing|impeller|gasket|sensor|coupling)\b", lowered):
            entities.append(
                {
                    "type": "Component",
                    "name": "Component",
                    "confidence": 0.68,
                    "evidence": text.strip(),
                    "source_document": document_id,
                    "chunk_id": chunk_id,
                    "chunk_index": chunk_index,
                }
            )

        if re.search(r"\b(?:vibration|leak|overheat|failure|noise|cavitation|corrosion)\b", lowered):
            entities.append(
                {
                    "type": "Symptom",
                    "name": "Symptom",
                    "confidence": 0.65,
                    "evidence": text.strip(),
                    "source_document": document_id,
                    "chunk_id": chunk_id,
                    "chunk_index": chunk_index,
                }
            )

        if re.search(r"\b(?:inspect|inspection|check)\b", lowered):
            entities.append(
                {
                    "type": "Inspection",
                    "name": "Inspection",
                    "confidence": 0.72,
                    "evidence": text.strip(),
                    "source_document": document_id,
                    "chunk_id": chunk_id,
                    "chunk_index": chunk_index,
                }
            )

        if re.search(r"\b(?:work order|wo[- ]?\d+|workorder)\b", lowered):
            entities.append(
                {
                    "type": "WorkOrder",
                    "name": "WorkOrder",
                    "confidence": 0.7,
                    "evidence": text.strip(),
                    "source_document": document_id,
                    "chunk_id": chunk_id,
                    "chunk_index": chunk_index,
                }
            )

        if re.search(r"\b(?:incident|accident|shutdown)\b", lowered):
            entities.append(
                {
                    "type": "Incident",
                    "name": "Incident",
                    "confidence": 0.7,
                    "evidence": text.strip(),
                    "source_document": document_id,
                    "chunk_id": chunk_id,
                    "chunk_index": chunk_index,
                }
            )

        if re.search(r"\b(?:location|area|room|building|plant|field)\b", lowered):
            entities.append(
                {
                    "type": "Location",
                    "name": "Location",
                    "confidence": 0.66,
                    "evidence": text.strip(),
                    "source_document": document_id,
                    "chunk_id": chunk_id,
                    "chunk_index": chunk_index,
                }
            )

        return entities

    @staticmethod
    def _normalize_llm_content(response: Any) -> str:
        if isinstance(response, str):
            return response
        if isinstance(response, dict):
            content = response.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                return "\n".join(str(item) for item in content)
            return json.dumps(content)
        if hasattr(response, "content"):
            content = response.content
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                return "\n".join(str(item) for item in content)
            return json.dumps(content)
        return str(response)

    @staticmethod
    def _parse_json_payload(content: str | Any) -> Any:
        if isinstance(content, (list, dict)):
            return content
        text = str(content or "").strip()
        if not text:
            return []
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\[.*\]", text, flags=re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    return []
            return []
