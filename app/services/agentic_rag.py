from __future__ import annotations

import logging
import re
import time
from typing import Any

logger = logging.getLogger(__name__)
class BaseTool:
    name: str = ""
    description: str = ""

    def execute(self, query: str, state: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class VectorSearchTool(BaseTool):
    def __init__(self, embedding_service: Any | None = None, qdrant_service: Any | None = None) -> None:
        self.name = "vector_search"
        self.description = "Retrieve semantically relevant chunks from the vector store."
        self.embedding_service = embedding_service
        self.qdrant_service = qdrant_service

    def execute(self, query: str, state: dict[str, Any]) -> dict[str, Any]:
        if not self.embedding_service or not self.qdrant_service:
            return {"context": "", "sources": [], "document_ids": []}

        vector = self.embedding_service.embed_texts([query])[0]
        if hasattr(vector, "detach"):
            vector = vector.detach().cpu().tolist()
        elif hasattr(vector, "tolist"):
            vector = vector.tolist()

        query_filter = None
        document_ids = state.get("document_ids", []) or []
        if document_ids:
            from qdrant_client.http import models as rest

            query_filter = rest.Filter(
                must=[
                    rest.FieldCondition(
                        key="document_id",
                        match=rest.MatchAny(any=[str(item) for item in document_ids if str(item).strip()]),
                    )
                ]
            )

        start = time.perf_counter()
        points = self.qdrant_service.query_vectors(vector, limit=3, filter=query_filter)
        elapsed = (time.perf_counter() - start) * 1000
        # metrics_service.record_vector_time(elapsed)
        return self._format_points(points)

    def _format_points(self, points: list[Any]) -> dict[str, Any]:
        blocks: list[str] = []
        sources: list[dict[str, Any]] = []
        document_ids: set[str] = set()

        for index, point in enumerate(points, start=1):
            payload = point.payload or {}
            chunk_text = str(payload.get("text", "")).strip()
            document_id = str(payload.get("document_id", "")).strip()
            original_filename = str(payload.get("original_filename", "")).strip()
            chunk_index = payload.get("chunk_index", 0)
            score = float(point.score) if getattr(point, "score", None) is not None else None

            citation = f"{original_filename or document_id}#{chunk_index}"
            if chunk_text:
                blocks.append(
                    f"[{index}]\nSource: {citation}\nSimilarity score: {score}\n\n{chunk_text}"
                )
            if document_id:
                document_ids.add(document_id)
            sources.append(
                {
                    "document_id": document_id,
                    "chunk_index": chunk_index,
                    "original_filename": original_filename,
                    "text": chunk_text,
                    "score": score,
                    "citation": citation,
                }
            )

        return {
            "context": "\n\n---\n\n".join(blocks),
            "sources": sources,
            "document_ids": sorted(document_ids),
        }


class GraphSearchTool(BaseTool):
    def __init__(self, graph_service: Any | None = None) -> None:
        self.name = "graph_search"
        self.description = "Use graph relationships from Neo4j to retrieve entity-linked facts."
        self.graph_service = graph_service

    def execute(self, query: str, state: dict[str, Any]) -> dict[str, Any]:
        if not self.graph_service:
            return {"context": "", "sources": [], "document_ids": []}

        result = self.graph_service.retrieve_context(query)
        facts = result.get("facts", [])
        document_ids = result.get("document_ids", [])
        if not facts:
            return {"context": "", "sources": [], "document_ids": document_ids}

        context = "Graph facts:\n" + "\n".join(facts)
        return {"context": context, "sources": [], "document_ids": document_ids}


class MetadataSearchTool(BaseTool):
    def __init__(self, qdrant_service: Any | None = None) -> None:
        self.name = "metadata_search"
        self.description = "Search payload metadata such as filenames and document IDs."
        self.qdrant_service = qdrant_service

    def execute(self, query: str, state: dict[str, Any]) -> dict[str, Any]:
        if not self.qdrant_service:
            return {"context": "", "sources": [], "document_ids": []}

        try:
            from qdrant_client.http import models as rest

            response = self.qdrant_service.client.scroll(
                collection_name=self.qdrant_service.collection_name,
                limit=20,
                with_payload=True,
                with_vectors=False,
            )
            points = list(response[0]) if response and response[0] else []
        except Exception as exc:  # pragma: no cover - defensive path
            logger.warning("Metadata search failed: %s", exc)
            return {"context": "", "sources": [], "document_ids": []}

        search_terms = [token for token in re.split(r"[^a-z0-9]+", query.lower()) if token]
        if not search_terms:
            return {"context": "", "sources": [], "document_ids": []}

        matching_points: list[Any] = []
        for point in points:
            payload = point.payload or {}
            metadata_text = " ".join(
                str(payload.get(key, ""))
                for key in ["document_id", "original_filename", "file_type", "source_type"]
            ).lower()
            if any(term in metadata_text for term in search_terms):
                matching_points.append(point)

        if not matching_points:
            return {"context": "", "sources": [], "document_ids": []}

        blocks: list[str] = []
        document_ids: set[str] = set()
        for index, point in enumerate(matching_points, start=1):
            payload = point.payload or {}
            document_id = str(payload.get("document_id", "")).strip()
            if document_id:
                document_ids.add(document_id)
            original_filename = str(payload.get("original_filename", "")).strip()
            chunk_index = payload.get("chunk_index", 0)
            metadata_summary = ", ".join(
                f"{key}={payload.get(key)}" for key in ["document_id", "original_filename", "file_type"] if payload.get(key)
            )
            blocks.append(f"[{index}] Metadata match: {metadata_summary}")

        return {"context": "\n\n---\n\n".join(blocks), "sources": [], "document_ids": sorted(document_ids)}


class DocumentLookupTool(BaseTool):
    def __init__(self, embedding_service: Any | None = None, qdrant_service: Any | None = None) -> None:
        self.name = "document_lookup"
        self.description = "Lookup specific documents or the most relevant document for the query."
        self.embedding_service = embedding_service
        self.qdrant_service = qdrant_service

    def execute(self, query: str, state: dict[str, Any]) -> dict[str, Any]:
        if not self.embedding_service or not self.qdrant_service:
            return {"context": "", "sources": [], "document_ids": []}

        document_ids = [str(item) for item in state.get("document_ids", []) if str(item).strip()]
        if not document_ids:
            match = re.search(r"document(?: id)?\s*[:#]?\s*([A-Za-z0-9._-]+)", query, flags=re.IGNORECASE)
            if match:
                document_ids = [match.group(1)]
        if not document_ids:
            return {"context": "", "sources": [], "document_ids": []}

        from qdrant_client.http import models as rest

        vector = self.embedding_service.embed_texts([query])[0]
        if hasattr(vector, "detach"):
            vector = vector.detach().cpu().tolist()
        elif hasattr(vector, "tolist"):
            vector = vector.tolist()

        query_filter = rest.Filter(
            must=[
                rest.FieldCondition(
                    key="document_id",
                    match=rest.MatchAny(any=document_ids),
                )
            ]
        )
        points = self.qdrant_service.query_vectors(vector, limit=3, filter=query_filter)
        return VectorSearchTool._format_points(self, points)  # type: ignore[arg-type]


class SimilarIncidentSearchTool(BaseTool):
    def __init__(self, embedding_service: Any | None = None, qdrant_service: Any | None = None) -> None:
        self.name = "similar_incident_search"
        self.description = "Search for previously similar incidents or failure cases."
        self.embedding_service = embedding_service
        self.qdrant_service = qdrant_service

    def execute(self, query: str, state: dict[str, Any]) -> dict[str, Any]:
        expanded_query = f"{query} similar incident previous case"
        return VectorSearchTool(self.embedding_service, self.qdrant_service).execute(expanded_query, state)


class MaintenanceHistoryTool(BaseTool):
    def __init__(self, embedding_service: Any | None = None, qdrant_service: Any | None = None) -> None:
        self.name = "maintenance_history"
        self.description = "Retrieve maintenance, repair, and service history context."
        self.embedding_service = embedding_service
        self.qdrant_service = qdrant_service

    def execute(self, query: str, state: dict[str, Any]) -> dict[str, Any]:
        expanded_query = f"{query} maintenance history repair service log"
        return VectorSearchTool(self.embedding_service, self.qdrant_service).execute(expanded_query, state)


class AssetInformationTool(BaseTool):
    def __init__(self, graph_service: Any | None = None) -> None:
        self.name = "asset_information"
        self.description = "Use graph relationships to explain asset context and dependencies."
        self.graph_service = graph_service

    def execute(self, query: str, state: dict[str, Any]) -> dict[str, Any]:
        if not self.graph_service:
            return {"context": "", "sources": [], "document_ids": []}
        result = self.graph_service.retrieve_context(query)
        facts = result.get("facts", [])
        return {
            "context": "Asset context:\n" + "\n".join(facts) if facts else "",
            "sources": [],
            "document_ids": result.get("document_ids", []),
        }


class ComplianceCheckerTool(BaseTool):
    def __init__(self, embedding_service: Any | None = None, qdrant_service: Any | None = None) -> None:
        self.name = "compliance_checker"
        self.description = "Pull compliance, procedure, and policy-related context."
        self.embedding_service = embedding_service
        self.qdrant_service = qdrant_service

    def execute(self, query: str, state: dict[str, Any]) -> dict[str, Any]:
        expanded_query = f"{query} compliance regulation policy audit"
        return VectorSearchTool(self.embedding_service, self.qdrant_service).execute(expanded_query, state)


class RootCauseSearchTool(BaseTool):
    def __init__(self, embedding_service: Any | None = None, qdrant_service: Any | None = None) -> None:
        self.name = "root_cause_search"
        self.description = "Search for root-cause analysis and failure explanations."
        self.embedding_service = embedding_service
        self.qdrant_service = qdrant_service

    def execute(self, query: str, state: dict[str, Any]) -> dict[str, Any]:
        expanded_query = f"{query} root cause failure analysis explanation"
        return VectorSearchTool(self.embedding_service, self.qdrant_service).execute(expanded_query, state)


class SOPLookupTool(BaseTool):
    def __init__(self, embedding_service: Any | None = None, qdrant_service: Any | None = None) -> None:
        self.name = "sop_lookup"
        self.description = "Look up standard operating procedures and runbooks."
        self.embedding_service = embedding_service
        self.qdrant_service = qdrant_service

    def execute(self, query: str, state: dict[str, Any]) -> dict[str, Any]:
        expanded_query = f"{query} SOP standard operating procedure runbook"
        return VectorSearchTool(self.embedding_service, self.qdrant_service).execute(expanded_query, state)


class KnowledgeGapDetectorTool(BaseTool):
    def __init__(self) -> None:
        self.name = "knowledge_gap_detector"
        self.description = "Flag whether the gathered context is insufficient for a confident answer."

    def execute(self, query: str, state: dict[str, Any]) -> dict[str, Any]:
        if state.get("sources"):
            return {"context": "", "sources": [], "document_ids": []}
        return {
            "context": "The available knowledge base context is insufficient to answer this question confidently.",
            "sources": [],
            "document_ids": [],
        }


class ToolRegistry:
    def __init__(
        self,
        embedding_service: Any | None = None,
        qdrant_service: Any | None = None,
        graph_service: Any | None = None,
    ) -> None:
        self.tools: list[BaseTool] = [
            VectorSearchTool(embedding_service, qdrant_service),
            SimilarIncidentSearchTool(embedding_service, qdrant_service),
            RootCauseSearchTool(embedding_service, qdrant_service),
            GraphSearchTool(graph_service),
            MetadataSearchTool(qdrant_service),
            DocumentLookupTool(embedding_service, qdrant_service),
            MaintenanceHistoryTool(embedding_service, qdrant_service),
            AssetInformationTool(graph_service),
            ComplianceCheckerTool(embedding_service, qdrant_service),
            SOPLookupTool(embedding_service, qdrant_service),
            KnowledgeGapDetectorTool(),
        ]

    def get_tool(self, name: str) -> BaseTool | None:
        return next((tool for tool in self.tools if tool.name == name), None)

    def select_tools(self, query: str) -> list[BaseTool]:
        if not query or not query.strip():
            return [self.get_tool("vector_search") or self.tools[0]]

        lowered_query = query.lower()
        scored_tools: list[tuple[int, BaseTool]] = []
        for tool in self.tools:
            if tool.name == "knowledge_gap_detector":
                continue
            score = self._score_tool(tool, lowered_query)
            if score > 0:
                scored_tools.append((score, tool))

        if not scored_tools:
            return [self.get_tool("vector_search") or self.tools[0]]

        scored_tools.sort(key=lambda item: (-item[0], item[1].name))
        selected = [tool for _, tool in scored_tools[:5]]

        if self.get_tool("vector_search") not in selected:
            selected.append(self.get_tool("vector_search") or self.tools[0])

        selected = sorted(
            selected,
            key=lambda tool: (
                self._planning_priority(tool.name),
                -self._score_tool(tool, lowered_query),
                tool.name,
            ),
        )

        return selected

    def _planning_priority(self, tool_name: str) -> int:
        if tool_name == "graph_search":
            return 0
        if tool_name in {"metadata_search", "asset_information"}:
            return 1
        if tool_name in {"vector_search", "document_lookup"}:
            return 2
        return 3

    def _score_tool(self, tool: BaseTool, query: str) -> int:
        if tool.name == "vector_search":
            return 1
        if tool.name == "similar_incident_search" and any(word in query for word in ["incident", "similar", "previous", "case", "failure"]):
            return 4
        if tool.name == "root_cause_search" and any(word in query for word in ["root", "cause", "failure", "explain", "why"]):
            return 4
        if tool.name == "graph_search" and any(word in query for word in ["asset", "equipment", "pump", "motor", "component", "system", "relationship"]):
            return 3
        if tool.name == "maintenance_history" and any(word in query for word in ["maintenance", "history", "repair", "service", "preventive"]):
            return 3
        if tool.name == "asset_information" and any(word in query for word in ["asset", "equipment", "component", "pump", "motor"]):
            return 2
        if tool.name == "sop_lookup" and any(word in query for word in ["sop", "procedure", "runbook", "standard", "operating"]):
            return 3
        if tool.name == "compliance_checker" and any(word in query for word in ["compliance", "policy", "regulation", "audit", "standard"]):
            return 3
        if tool.name == "document_lookup" and any(word in query for word in ["document", "file", "report", "manual", "lookup"]):
            return 2
        if tool.name == "metadata_search" and any(word in query for word in ["metadata", "document", "filename", "id", "source"]):
            return 2
        if tool.name == "knowledge_gap_detector":
            return 1
        return 0


class AgenticRAGService:
    def __init__(
        self,
        embedding_service: Any | None = None,
        qdrant_service: Any | None = None,
        graph_service: Any | None = None,
    ) -> None:
        self.registry = ToolRegistry(embedding_service, qdrant_service, graph_service)
        self.reasoning_trace: list[dict[str, Any]] = []

    def run(self, question: str, top_k: int = 3) -> dict[str, Any]:
        state: dict[str, Any] = {
            "query": question,
            "context_blocks": [],
            "graph_context_blocks": [],
            "sources": [],
            "document_ids": [],
        }
        self.reasoning_trace = []
        retrieval_start = time.perf_counter()

        tools = self.registry.select_tools(question)
        if not tools:
            tools = [self.registry.get_tool("vector_search") or self.registry.tools[0]]

        used_tool_names: set[str] = set()
        for index, tool in enumerate(tools, start=1):
            if tool.name in used_tool_names:
                continue
            used_tool_names.add(tool.name)

            self.reasoning_trace.append(
                {
                    "step": index,
                    "tool": tool.name,
                    "reason": tool.description,
                }
            )
            result = tool.execute(question, state)
            state = self._merge_state(state, result, tool.name)

            if len(state.get("sources", [])) >= top_k * 2:
                break

        if not state.get("sources"):
            knowledge_tool = self.registry.get_tool("knowledge_gap_detector")
            if knowledge_tool:
                self.reasoning_trace.append(
                    {
                        "step": len(self.reasoning_trace) + 1,
                        "tool": knowledge_tool.name,
                        "reason": knowledge_tool.description,
                    }
                )
                state = self._merge_state(state, knowledge_tool.execute(question, state), knowledge_tool.name)

        graph_context = "\n\n---\n\n".join(state.get("graph_context_blocks", [])) if state.get("graph_context_blocks") else ""
        retrieval_context = "\n\n---\n\n".join(state.get("context_blocks", [])) if state.get("context_blocks") else ""

        context_sections: list[str] = []
        if graph_context:
            context_sections.append("Graph Facts:\n" + graph_context)
        if retrieval_context:
            context_sections.append("Retrieved Chunks:\n" + retrieval_context)

        context = ""
        if context_sections:
            context = "====================\n" + "\n\n--------------------\n\n".join(context_sections) + "\n===================="

        sources = self._dedupe_sources(state.get("sources", []))
        # metrics_service.record_retrieval_time((time.perf_counter() - retrieval_start) * 1000)

        return {
            "context": context,
            "sources": sources,
            "document_ids": state.get("document_ids", []),
            "reasoning_trace": self.reasoning_trace,
        }

    def _merge_state(self, state: dict[str, Any], tool_result: dict[str, Any], tool_name: str) -> dict[str, Any]:
        context = tool_result.get("context", "")
        if context:
            if tool_name in {"graph_search", "asset_information"}:
                state.setdefault("graph_context_blocks", []).append(context)
            else:
                state.setdefault("context_blocks", []).append(context)

        if self._should_add_sources(tool_name):
            for source in tool_result.get("sources", []):
                if source not in state.setdefault("sources", []):
                    state["sources"].append(source)

        for document_id in tool_result.get("document_ids", []):
            state.setdefault("document_ids", [])
            if str(document_id) not in [str(item) for item in state["document_ids"]]:
                state["document_ids"].append(document_id)

        return state

    def _should_add_sources(self, tool_name: str) -> bool:
        return tool_name in {
            "vector_search",
            "similar_incident_search",
            "root_cause_search",
            "maintenance_history",
            "compliance_checker",
            "sop_lookup",
            "document_lookup",
        }

    def _dedupe_sources(self, sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[tuple[str, int, str]] = set()
        deduped: list[dict[str, Any]] = []
        for source in sources:
            key = (
                str(source.get("document_id", "")),
                int(source.get("chunk_index", 0) or 0),
                str(source.get("citation", "")),
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(source)
        return deduped