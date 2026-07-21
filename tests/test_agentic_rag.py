from app.services.agentic_rag import GraphSearchTool, ToolRegistry


class FakeGraphService:
    def retrieve_context(self, query: str) -> dict[str, object]:
        return {
            "facts": ["Pump has component Motor"],
            "document_ids": ["doc-42"],
        }


def test_registry_prioritizes_relevant_tools_for_incident_queries() -> None:
    registry = ToolRegistry()

    selected_tools = registry.select_tools(
        "Find a similar incident and explain the root cause of the pump failure"
    )
    tool_names = [tool.name for tool in selected_tools]

    assert "vector_search" in tool_names
    assert "similar_incident_search" in tool_names
    assert "root_cause_search" in tool_names


def test_graph_search_does_not_return_graph_facts_as_sources() -> None:
    tool = GraphSearchTool(FakeGraphService())

    result = tool.execute("pump component", {})

    assert result["sources"] == []
    assert result["document_ids"] == ["doc-42"]
    assert "Graph facts" in result["context"]


def test_registry_orders_graph_search_before_vector_search() -> None:
    registry = ToolRegistry(graph_service=FakeGraphService())

    selected_tools = registry.select_tools("Explain the asset relationship for the pump")
    tool_names = [tool.name for tool in selected_tools]

    assert tool_names[0] == "graph_search"
    assert tool_names.index("graph_search") < tool_names.index("vector_search")
