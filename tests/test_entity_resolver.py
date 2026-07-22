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


def test_entity_extractor_finds_pid_entities_in_text():
    from app.services.entity_extractor import EntityExtractor

    extractor = EntityExtractor(model=None, api_key=None)
    text = "P&ID shows P101 feeding into CV-102 and PT101. The heat exchanger and main pipeline line 5 are visible."
    entities = extractor.extract_entities(
        text=text,
        document_id="doc-2",
        chunk_id="doc-2:1",
        chunk_index=1,
    )

    types = {entity["type"] for entity in entities}
    assert "EquipmentTag" in types
    assert "Valve" in types
    assert "Instrument" in types
    assert "Pipeline" in types
    assert "ProcessUnit" in types or "Asset" in types
