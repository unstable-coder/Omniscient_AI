from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class Neo4jLoader:
    """Build and optionally persist Neo4j graph payloads from resolved entities."""

    def __init__(self, uri: str | None = None, user: str | None = None, password: str | None = None) -> None:
        self.uri = uri or ""
        self.user = user or ""
        self.password = password or ""
        self._driver: Any | None = None

    def build_payloads(self, entities: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        nodes: list[dict[str, Any]] = []
        relationships: list[dict[str, Any]] = []

        if not entities:
            return nodes, relationships

        by_key: dict[str, dict[str, Any]] = {}
        document_id = None
        for entity in entities:
            if entity.get("source_document"):
                document_id = str(entity.get("source_document"))
            key = entity.get("canonical_key") or self._entity_key(entity)
            if key not in by_key:
                by_key[key] = {
                    "id": key,
                    "label": self._label_for(entity.get("type")),
                    "name": entity.get("canonical_name") or entity.get("name"),
                    "properties": {
                        "name": entity.get("canonical_name") or entity.get("name"),
                        "type": entity.get("type"),
                        "source_document": entity.get("source_document"),
                        "chunk_id": entity.get("chunk_id"),
                    },
                }
                nodes.append(by_key[key])

        if document_id:
            doc_node = {
                "id": f"document:{document_id}",
                "label": "Document",
                "name": document_id,
                "properties": {
                    "name": document_id,
                    "type": "Document",
                },
            }
            if not any(node["id"] == doc_node["id"] for node in nodes):
                nodes.append(doc_node)

        for entity in entities:
            source_key = entity.get("canonical_key") or self._entity_key(entity)
            if document_id:
                relationships.append(
                    {
                        "id": f"mentioned:{document_id}:{source_key}",
                        "source": f"document:{document_id}",
                        "target": source_key,
                        "type": "MENTIONED_IN",
                        "properties": {
                            "source_document": document_id,
                            "chunk_id": entity.get("chunk_id"),
                            "confidence": entity.get("confidence", 0.0),
                            "evidence_text": entity.get("evidence") or "",
                        },
                    }
                )

            for related in entities:
                if related is entity:
                    continue
                if entity.get("chunk_id") != related.get("chunk_id"):
                    continue
                relation_type = self._relationship_type(entity, related)
                if not relation_type:
                    continue
                relationships.append(
                    {
                        "id": f"{relation_type.lower()}:{source_key}:{related.get('canonical_key') or self._entity_key(related)}",
                        "source": source_key,
                        "target": related.get("canonical_key") or self._entity_key(related),
                        "type": relation_type,
                        "properties": {
                            "source_document": entity.get("source_document"),
                            "chunk_id": entity.get("chunk_id"),
                            "confidence": max(entity.get("confidence", 0.0), related.get("confidence", 0.0)),
                            "evidence_text": related.get("evidence") or entity.get("evidence") or "",
                        },
                    }
                )

        return nodes, relationships

    def persist(self, entities: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        nodes, relationships = self.build_payloads(entities)
        if not self.uri:
            logger.info("Neo4j URI not configured; skipping persist")
            return nodes, relationships

        try:
            from neo4j import GraphDatabase
        except Exception as exc:  # pragma: no cover - defensive path
            logger.warning("neo4j driver unavailable: %s", exc)
            return nodes, relationships

        if self._driver is None:
            self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

        with self._driver.session() as session:
            for node in nodes:
                session.run(
                    f"MERGE (n:{node['label']} {{id: $id}}) SET n += $properties",
                    id=node["id"],
                    properties=node["properties"],
                )
            for rel in relationships:
                session.run(
                    (
                        f"MATCH (source {{id: $source}}) "
                        f"MATCH (target {{id: $target}}) "
                        f"MERGE (source)-[r:{rel['type']} {{id: $id}}]->(target) "
                        f"SET r += $properties"
                    ),
                    id=rel["id"],
                    source=rel["source"],
                    target=rel["target"],
                    properties=rel["properties"],
                )
        return nodes, relationships

    @staticmethod
    def _entity_key(entity: dict[str, Any]) -> str:
        entity_type = str(entity.get("type", "")).strip()
        canonical_name = str(entity.get("canonical_name") or entity.get("name") or "").strip()
        return f"{entity_type}:{canonical_name.lower()}"

    @staticmethod
    def _label_for(entity_type: Any) -> str:
        mapping = {
            "Asset": "Asset",
            "Component": "Component",
            "Document": "Document",
            "Inspection": "Inspection",
            "WorkOrder": "WorkOrder",
            "Incident": "Incident",
            "Symptom": "Symptom",
            "FailureMode": "FailureMode",
            "Action": "Action",
            "Location": "Location",
            "EquipmentModel": "EquipmentModel",
            "EquipmentTag": "EquipmentTag",
            "Instrument": "Instrument",
            "Pipeline": "Pipeline",
            "Valve": "Valve",
            "Sensor": "Sensor",
            "ProcessUnit": "ProcessUnit",
        }
        return mapping.get(str(entity_type), "Asset")

    @staticmethod
    def _relationship_type(left: dict[str, Any], right: dict[str, Any]) -> str | None:
        left_type = str(left.get("type", "")).strip()
        right_type = str(right.get("type", "")).strip()

        relation_map = {
            ("Asset", "Component"): "HAS_COMPONENT",
            ("Asset", "Symptom"): "EXPERIENCED",
            ("Asset", "FailureMode"): "HAS_FAILURE",
            ("Asset", "Action"): "HAS_ACTION",
            ("Asset", "Inspection"): "INSPECTED_IN",
            ("Asset", "WorkOrder"): "WORKORDER_FOR",
            ("Asset", "Location"): "LOCATED_IN",
            ("Asset", "EquipmentTag"): "HAS_TAG",
            ("Asset", "Instrument"): "HAS_INSTRUMENT",
            ("Asset", "Pipeline"): "CONNECTED_TO",
            ("Asset", "Valve"): "HAS_VALVE",
            ("Asset", "Sensor"): "HAS_SENSOR",
            ("Asset", "ProcessUnit"): "PART_OF",
            ("ProcessUnit", "Asset"): "CONTAINS",
            ("EquipmentTag", "Instrument"): "INDICATES",
            ("Pipeline", "Valve"): "CONTAINS",
            ("Pipeline", "Sensor"): "MONITORED_BY",
            ("Component", "Symptom"): "RELATED_TO",
            ("Component", "FailureMode"): "RELATED_TO",
            ("Component", "Action"): "RELATED_TO",
            ("Symptom", "FailureMode"): "RELATED_TO",
            ("Incident", "Action"): "HAS_ACTION",
        }
        return relation_map.get((left_type, right_type)) or relation_map.get((right_type, left_type))
