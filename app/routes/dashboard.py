from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from pathlib import Path

from qdrant_client import QdrantClient

from app.config import settings
from app.services.metrics_service import MetricsService, metrics_service
from app.services.neo4j_loader import Neo4jLoader
from app.services.status_service import StatusService

router = APIRouter()
metrics_service = MetricsService()
status_service = StatusService()

templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent / "utils" / "templates")


@router.get("/dashboard")
def dashboard_page(request: Request) -> str:
    return templates.TemplateResponse(request=request, name="dashboard.html", context={"request": request})


@router.get("/dashboard/stats")
def dashboard_stats() -> dict[str, object]:
    documents = status_service.list_documents()

    indexed = sum(1 for item in documents if item.status == "INDEXED")
    processing = sum(1 for item in documents if item.status == "PROCESSING")
    failed = sum(1 for item in documents if item.status == "FAILED")
    chunks_created = sum(int(item.chunk_count or 0) for item in documents)

    vectors_stored = 0
    try:
        client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)
        collection_info = client.get_collection(collection_name=settings.QDRANT_COLLECTION)
        points_count = getattr(collection_info, "points_count", None)
        if hasattr(points_count, "value"):
            points_count = points_count.value
        vectors_stored = int(points_count or 0)
    except Exception:
        vectors_stored = 0

    graph_nodes = 0
    graph_relationships = 0
    try:
        loader = Neo4jLoader(uri=settings.NEO4J_URI, user=settings.NEO4J_USER, password=settings.NEO4J_PASSWORD)
        if loader.uri:
            from neo4j import GraphDatabase

            driver = GraphDatabase.driver(loader.uri, auth=(loader.user, loader.password))
            with driver.session() as session:
                graph_nodes = int(session.run("MATCH (n) RETURN count(n) AS count").single()["count"])
                graph_relationships = int(session.run("MATCH ()-[r]->() RETURN count(r) AS count").single()["count"])
    except Exception:
        graph_nodes = 0
        graph_relationships = 0

    return {
        "documents_indexed": indexed,
        "documents_processing": processing,
        "documents_failed": failed,
        "chunks_created": chunks_created,
        "vectors_stored": vectors_stored,
        "graph_nodes": graph_nodes,
        "graph_relationships": graph_relationships,
        **metrics_service.get_metrics_snapshot(),
    }
