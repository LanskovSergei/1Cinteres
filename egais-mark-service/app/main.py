"""HTTP API сервиса.

1С присылает данные, сервис применяет правила и возвращает решение.
Ничего в базе 1С не меняется: запись остаётся за обработкой.
"""
from __future__ import annotations

import os

from fastapi import Depends, FastAPI, Header, HTTPException

from app.engine import codes as codes_mod
from app.engine.matching import match
from app.engine.reconcile import reconcile
from app.logging_setup import event, timed
from app.metrics import metrics
from app.models import (
    InventoryParseRequest,
    InventoryParseResponse,
    MatchRequest,
    MatchResponse,
    ReconcileRequest,
    ReconcileResponse,
)

VERSION = "0.1.0"

app = FastAPI(
    title="egais-mark-service",
    version=VERSION,
    description="Сверка акцизных марок: правила вынесены из модулей 1С",
)


def check_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Если ключ задан в окружении, 1С обязана его передавать."""
    expected = os.getenv("API_KEY", "")
    if expected and x_api_key != expected:
        raise HTTPException(status_code=401, detail="Неверный или отсутствующий X-API-Key")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": VERSION}


@app.get("/v1/metrics/summary")
def metrics_summary(_: None = Depends(check_api_key)) -> dict:
    return metrics.summary()


@app.post("/v1/reconcile", response_model=ReconcileResponse)
def reconcile_endpoint(
    req: ReconcileRequest, _: None = Depends(check_api_key)
) -> ReconcileResponse:
    failed = False
    try:
        with timed("reconcile", reference=req.reference, marks=len(req.marks)) as t:
            result = reconcile(req)
    except Exception:
        failed = True
        event("reconcile_failed", reference=req.reference)
        raise
    finally:
        metrics.observe(len(req.marks), t.get("elapsed_ms", 0) if not failed else 0, failed)

    result.elapsed_ms = t["elapsed_ms"]
    return result


@app.post("/v1/inventory/parse", response_model=InventoryParseResponse)
def inventory_parse(
    req: InventoryParseRequest, _: None = Depends(check_api_key)
) -> InventoryParseResponse:
    with timed("inventory_parse", size=len(req.content or "")) as t:
        codes = codes_mod.parse_inventory(req.content)

    return InventoryParseResponse(codes=codes, count=len(codes), elapsed_ms=t["elapsed_ms"])


@app.post("/v1/nomenclature/match", response_model=MatchResponse)
def nomenclature_match(
    req: MatchRequest, _: None = Depends(check_api_key)
) -> MatchResponse:
    with timed("nomenclature_match", candidates=len(req.candidates)) as t:
        result = match(req)

    result.elapsed_ms = t["elapsed_ms"]
    return result
