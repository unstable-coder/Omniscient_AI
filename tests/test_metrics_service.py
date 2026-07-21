from app.services.metrics_service import MetricsService


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
