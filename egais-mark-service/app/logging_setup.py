"""Структурные логи и замер времени.

Требование заказчика: видеть время обработки каждой марки, иначе после теста
на 200 актах нельзя оценить производительность.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        extra = getattr(record, "extra_fields", None)
        if extra:
            payload.update(extra)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging() -> logging.Logger:
    level = os.getenv("LOG_LEVEL", "INFO").upper()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    return logging.getLogger("egais")


log = setup_logging()


def event(message: str, **fields) -> None:
    log.info(message, extra={"extra_fields": fields})


@contextmanager
def timed(operation: str, **fields):
    """Замер операции. В словарь result попадает elapsed_ms — он же уходит в ответ API."""
    started = time.perf_counter()
    result: dict[str, float] = {}
    try:
        yield result
    finally:
        elapsed = (time.perf_counter() - started) * 1000
        result["elapsed_ms"] = round(elapsed, 2)
        marks = fields.get("marks") or 0
        if marks:
            fields["ms_per_mark"] = round(elapsed / marks, 2)
        event(operation, elapsed_ms=result["elapsed_ms"], **fields)
