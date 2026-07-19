from __future__ import annotations

import logging
from typing import Any

from app.config import settings
from app.services.entity_extractor import EntityExtractor
from app.services.entity_resolver import EntityResolver

logger = logging.getLogger(__name__)


class GraphRetrievalService:
    """Retrieve graph facts from Neo4j and return document IDs for hybrid retrieval."""

    def __init__(self) -> None:
        self.entity_extractor = EntityExtractor()
        self.entity_resolver = EntityResolver()
        self.uri = settings.NEO4J_URI
        self.user = settings.NEO4J_USER
        self.password = settings.NEO4J_PASSWORD
        self._driver: Any | None = None

    def detect_entities(self, question: str) -> list[dict[str, Any]]:
        if not question or not question.strip():
            return []

        try:
            entities = self.entity_extractor.extract_entities(
                text=question,
                document_id="query",
                chunk_id="query",
                chunk_index=0,
            )
            if not entities:
                return []
            return self.entity_resolver.resolve_entities(entities)
        except Exception as exc:  # pragma: no cover - defensive path
            logger.warning("Entity detection failed for query: %s", exc)
            return []

    def retrieve_context(self, question: str) -> dict[str, Any]:
        entities = self.detect_entities(question)
        if not entities:
            return {"entities": [], "facts": [], "document_ids": []}

        if not self.uri:
            logger.info("Neo4j URI not configured; skipping graph retrieval")
            return {"entities": entities, "facts": [], "document_ids": []}

        try:
            from neo4j import GraphDatabase
        except Exception as exc:  # pragma: no cover - defensive path
            logger.warning("neo4j driver unavailable: %s", exc)
            return {"entities": entities, "facts": [], "document_ids": []}

        if self._driver is None:
            self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

        facts: list[str] = []
        document_ids: set[str] = set()

        with self._driver.session() as session:
            for entity in entities:
                print("Searching Neo4j for:", entity)

                entity_name = str(entity.get("canonical_name") or entity.get("name") or "").strip()
                if not entity_name:
                    continue
                result = session.run(
                    """
                    MATCH (source)-[r]->(target)
                    WHERE toLower(coalesce(source.name, '')) CONTAINS toLower($name)
                       OR toLower(coalesce(target.name, '')) CONTAINS toLower($name)
                    RETURN source, type(r) AS relationship_type, target
                    LIMIT 10
                    """,
                    name=entity_name,
                )
                for record in result:
                    source = record["source"]
                    target = record["target"]
                    rel_type = record["relationship_type"]
                    source_name = source.get("name") or source.id
                    target_name = target.get("name") or target.id
                    source_doc = source.get("source_document") or source.get("name")
                    target_doc = target.get("source_document") or target.get("name")
                    if source_doc:
                        document_ids.add(str(source_doc))
                    if target_doc:
                        document_ids.add(str(target_doc))
                    facts.append(
                        f"{source_name} --[{rel_type}]--> {target_name}"
                    )

        unique_facts = list(dict.fromkeys(facts))
        return {
            "entities": entities,
            "facts": unique_facts,
            "document_ids": sorted(document_ids),
        }
