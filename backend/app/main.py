"""Veridata FastAPI app: observability foundation (task 2)."""
from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request
from opentelemetry import trace

from .telemetry import init_telemetry

app = FastAPI(title="Veridata")
init_telemetry(app)

tracer = trace.get_tracer("veridata")


def _current_trace_id() -> str:
    ctx = trace.get_current_span().get_span_context()
    if ctx.trace_id:
        return format(ctx.trace_id, "032x")
    return ""


@app.middleware("http")
async def trace_id_header(request: Request, call_next):
    response = await call_next(request)
    trace_id = _current_trace_id()
    if trace_id:
        response.headers["X-Trace-Id"] = trace_id
    return response


@app.get("/health")
def health():
    with tracer.start_as_current_span("health.check") as span:
        span.set_attribute("veridata.check", "ok")
        return {"status": "ok", "trace_id": _current_trace_id()}
