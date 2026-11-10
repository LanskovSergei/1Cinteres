from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
CODE = "1" * 70


def test_health():
    assert client.get("/health").json()["status"] == "ok"


def test_reconcile_returns_timing():
    payload = {
        "reference": "FB-1",
        "marks": [{"code": CODE, "status": "Реализована", "moved_at": "2026-09-01T00:00:00"}],
        "egais": {"codes": [CODE], "received_at": "2026-10-01T12:00:00"},
    }
    body = client.post("/v1/reconcile", json=payload).json()
    assert body["status_changes"][0]["new_status"] == "ВНаличии"
    assert body["elapsed_ms"] >= 0
    assert body["marks_processed"] == 1


def test_inventory_parse():
    body = client.post("/v1/inventory/parse", json={"content": f"a;{CODE}"}).json()
    assert body["codes"] == [CODE] and body["count"] == 1


def test_metrics_summary():
    body = client.get("/v1/metrics/summary").json()
    assert "marks" in body and "avg_ms_per_mark" in body
