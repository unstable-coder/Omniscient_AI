from app.services.agentic_rag import ToolRegistry


def test_registry_prioritizes_relevant_tools_for_incident_queries() -> None:
    registry = ToolRegistry()

    selected_tools = registry.select_tools(
        "Find a similar incident and explain the root cause of the pump failure"
    )
    tool_names = [tool.name for tool in selected_tools]

    assert "vector_search" in tool_names
    assert "similar_incident_search" in tool_names
    assert "root_cause_search" in tool_names
