from app.services.neo4j_loader import Neo4jLoader


def test_loader_builds_node_and_relationship_payloads():
    loader = Neo4jLoader(uri="bolt://localhost:7687", user="neo4j", password="test")
    payload = [
        {
            "type": "Asset",
            "name": "Pump 101",
            "confidence": 0.95,
            "evidence": "Pump 101",
            "canonical_name": "P101",
            "source_document": "doc-1",
            "chunk_id": "chunk-1",
        },
        {
            "type": "Component",
            "name": "Seal",
            "confidence": 0.9,
            "evidence": "Seal failure",
            "canonical_name": "Seal",
            "source_document": "doc-1",
            "chunk_id": "chunk-1",
        },
    ]

    nodes, relationships = loader.build_payloads(payload)

    assert any(node["label"] == "Asset" for node in nodes)
    assert any(rel["type"] == "HAS_COMPONENT" for rel in relationships)
