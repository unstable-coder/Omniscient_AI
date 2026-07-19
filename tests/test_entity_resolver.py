from app.services.entity_resolver import EntityResolver


def test_resolve_entities_unifies_aliases_to_one_asset():
    resolver = EntityResolver()
    entities = [
        {"type": "Asset", "name": "P101", "confidence": 0.95, "evidence": "Pump P101"},
        {"type": "Asset", "name": "P-101", "confidence": 0.95, "evidence": "P-101"},
        {"type": "Asset", "name": "Pump 101", "confidence": 0.95, "evidence": "Pump 101"},
        {"type": "Asset", "name": "Cooling Water Pump A", "confidence": 0.92, "evidence": "Cooling Water Pump A"},
    ]

    resolved = resolver.resolve_entities(entities)
    canonical_names = {entity["canonical_name"] for entity in resolved}

    assert len(canonical_names) == 1
    assert "P101" in canonical_names
