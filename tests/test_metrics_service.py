from fastapi.testclient import TestClient

from app.main import app
from app.services.metrics_service import MetricsService, metrics_service


def test_metrics_service_tracks_average_timings() -> None:
    service = MetricsService()

    service.record_embedding_time(10)
    service.record_embedding_time(20)
    service.record_vector_time(15)
    service.record_graph_time(25)
    service.record_response_time(40)
    service.record_retrieval_time(50)

    assert service.get_average_embedding_time_ms() == 15.0
    assert service.get_average_vector_time_ms() == 15.0
    assert service.get_average_graph_time_ms() == 25.0
    assert service.get_average_response_time_ms() == 40.0
    assert service.get_average_retrieval_time_ms() == 50.0


def test_dashboard_stats_uses_shared_metrics_service() -> None:
    metrics_service._embedding_times.clear()
    metrics_service._vector_times.clear()
    metrics_service._graph_times.clear()
    metrics_service._response_times.clear()
    metrics_service._retrieval_times.clear()

    metrics_service.record_embedding_time(12.5)
    metrics_service.record_vector_time(18.0)
    metrics_service.record_graph_time(22.0)
    metrics_service.record_response_time(33.0)
    metrics_service.record_retrieval_time(44.0)

    client = TestClient(app)
    response = client.get("/api/dashboard/stats")

    assert response.status_code == 200
    payload = response.json()
    assert payload["average_embedding_time_ms"] == 12.5
    assert payload["average_vector_query_time_ms"] == 18.0
    assert payload["average_graph_query_time_ms"] == 22.0
    assert payload["average_response_time_ms"] == 33.0
    assert payload["average_retrieval_time_ms"] == 44.0
