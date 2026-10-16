from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.llm import MockLLM
from app.main import app, get_llm, get_verify_llm

SAMPLE = Path(__file__).parent / "data" / "sample.csv"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("VERIDATA_RUN_RECORDS_DIR", str(tmp_path))
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _upload(client):
    with open(SAMPLE, "rb") as f:
        return client.post("/upload", files={"file": ("sample.csv", f, "text/csv")})


def test_upload_returns_columns_and_row_count(client):
    resp = _upload(client)
    assert resp.status_code == 200
    body = resp.json()
    assert body["row_count"] == 6
    assert {c["name"] for c in body["columns"]} == {"id", "name", "department", "salary"}


def test_ask_returns_answer_sql_confidence_and_trace_id(client):
    app.dependency_overrides[get_llm] = lambda: MockLLM("SELECT count(*) AS n FROM data")
    app.dependency_overrides[get_verify_llm] = lambda: MockLLM(
        responses=["SELECT count(*) AS n FROM data", "VERDICT: yes"]
    )
    _upload(client)
    resp = client.post("/ask", json={"question": "how many rows?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["sql"] == "SELECT count(*) AS n FROM data"
    assert body["answer"]["rows"] == [[6]]  # JSON turns the tuple into a list
    assert body["confidence"] == "high"
    assert any(c["name"] == "judge" for c in body["checks"])
    assert len(body["trace_id"]) == 32


def test_ask_low_confidence_still_returns_200_with_reason(client):
    app.dependency_overrides[get_llm] = lambda: MockLLM("SELECT count(*) AS n FROM data")
    app.dependency_overrides[get_verify_llm] = lambda: MockLLM(
        responses=["SELECT count(*) AS n FROM data", "VERDICT: no wrong column"]
    )
    _upload(client)
    resp = client.post("/ask", json={"question": "how many rows?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["confidence"] == "low"
    assert body["abstained"] is True
    assert body["reason"]


def test_ask_guard_rejection_returns_error_and_trace_id(client):
    app.dependency_overrides[get_llm] = lambda: MockLLM("DROP TABLE data")
    app.dependency_overrides[get_verify_llm] = lambda: MockLLM("unused")
    _upload(client)
    resp = client.post("/ask", json={"question": "drop it"})
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert "rejected" in detail["error"]
    assert detail["sql"] == "DROP TABLE data"
    assert len(detail["trace_id"]) == 32


def test_ask_without_upload_is_rejected():
    # fresh client with no uploaded dataset would need module isolation; instead
    # assert the clear 400 path exists via the dependency on _dataset being None.
    import app.main as main

    main._dataset = None
    with TestClient(app) as c:
        resp = c.post("/ask", json={"question": "x"})
    assert resp.status_code == 400
