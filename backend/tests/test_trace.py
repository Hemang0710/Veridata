"""Spec 001 trace requirement: every /ask emits one span per step and the
request's trace ID reaches the client (body + X-Trace-Id header)."""

import pytest
from fastapi.testclient import TestClient
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app.llm import MockLLM
from app.main import app, get_llm

# span per step the spec names: schema build, model call, guard, execution (+ persist)
STEP_SPANS = {
    "schema.build_summary",
    "llm.call",
    "guard.check",
    "executor.run",
    "run_record.persist",
    "pipeline.run",
}


@pytest.fixture
def spans():
    provider = trace.get_tracer_provider()
    if not isinstance(provider, TracerProvider):
        provider = TracerProvider()
        trace.set_tracer_provider(provider)
    exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    exporter.clear()
    return exporter


def test_ask_emits_span_per_step_and_returns_trace_id(tmp_path, monkeypatch, spans):
    monkeypatch.setenv("VERIDATA_RUN_RECORDS_DIR", str(tmp_path))
    app.dependency_overrides[get_llm] = lambda: MockLLM("SELECT count(*) AS n FROM data")
    try:
        with TestClient(app) as c:
            with open("tests/data/sample.csv", "rb") as f:
                c.post("/upload", files={"file": ("sample.csv", f, "text/csv")})
            resp = c.post("/ask", json={"question": "how many rows?"})
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    trace_id = resp.json()["trace_id"]
    assert resp.headers["X-Trace-Id"] == trace_id  # same id on the header

    emitted = {s.name for s in spans.get_finished_spans()}
    assert STEP_SPANS <= emitted, f"missing spans: {STEP_SPANS - emitted}"
