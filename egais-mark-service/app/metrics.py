"""Счётчики для ответа на вопрос «сколько марок система обрабатывает за день»."""
from __future__ import annotations

import threading
from collections import defaultdict
from datetime import date


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._marks: dict[date, int] = defaultdict(int)
        self._requests: dict[date, int] = defaultdict(int)
        self._errors: dict[date, int] = defaultdict(int)
        self._total_ms: dict[date, float] = defaultdict(float)

    def observe(self, marks: int, elapsed_ms: float, failed: bool = False) -> None:
        today = date.today()
        with self._lock:
            self._requests[today] += 1
            self._marks[today] += marks
            self._total_ms[today] += elapsed_ms
            if failed:
                self._errors[today] += 1

    def summary(self) -> dict:
        today = date.today()
        with self._lock:
            marks = self._marks[today]
            total_ms = self._total_ms[today]
            return {
                "date": today.isoformat(),
                "requests": self._requests[today],
                "marks": marks,
                "errors": self._errors[today],
                "avg_ms_per_mark": round(total_ms / marks, 2) if marks else 0,
                "total_ms": round(total_ms, 2),
            }


metrics = Metrics()
