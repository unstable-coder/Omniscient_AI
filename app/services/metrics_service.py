from __future__ import annotations

from collections import deque
from typing import Deque


class MetricsService:
    def __init__(self) -> None:
        self._embedding_times: Deque[float] = deque(maxlen=200)
        self._vector_times: Deque[float] = deque(maxlen=200)
        self._graph_times: Deque[float] = deque(maxlen=200)
        self._response_times: Deque[float] = deque(maxlen=200)
        self._retrieval_times: Deque[float] = deque(maxlen=200)

    def record_embedding_time(self, ms: float) -> None:
        self._embedding_times.append(float(ms))

    def record_vector_time(self, ms: float) -> None:
        self._vector_times.append(float(ms))

    def record_graph_time(self, ms: float) -> None:
        self._graph_times.append(float(ms))

    def record_response_time(self, ms: float) -> None:
        self._response_times.append(float(ms))

    def record_retrieval_time(self, ms: float) -> None:
        self._retrieval_times.append(float(ms))

    def get_average_embedding_time_ms(self) -> float:
        return self._average(self._embedding_times)

    def get_average_vector_time_ms(self) -> float:
        return self._average(self._vector_times)

    def get_average_graph_time_ms(self) -> float:
        return self._average(self._graph_times)

    def get_average_response_time_ms(self) -> float:
        return self._average(self._response_times)

    def get_average_retrieval_time_ms(self) -> float:
        return self._average(self._retrieval_times)

    @staticmethod
    def _average(values: Deque[float]) -> float:
        if not values:
            return 0.0
        return round(sum(values) / len(values), 2)


metrics_service = MetricsService()