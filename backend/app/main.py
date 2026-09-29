"""Veridata FastAPI app: observability foundation (task 2)."""

from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()  # before telemetry reads the environment

from fastapi import FastAPI, Request  # noqa: E402
from opentelemetry import trace  # noqa: E402

from .telemetry import init_telemetry  # noqa: E402

app = FastAPI(title="Veridata")
init_telemetry(app)

tracer = trace.get_tracer("veridata")


def _current_trace_id() -> str:
    ctx = trace.get_current_span().get_span_context()
    return format(ctx.trace_id, "032x") if ctx.trace_id else ""


@app.middleware("http")
async def trace_id_header(request: Request, call_next):
    """Surface the request's trace ID so a bug report maps to a single trace."""
    response = await call_next(request)
    trace_id = _current_trace_id()
    if trace_id:
        response.headers["X-Trace-Id"] = trace_id
    return response


@app.get("/health")
def health():
    """Emit a test span so a trace shows up in Langfuse."""
    with tracer.start_as_current_span("health.check") as span:
        span.set_attribute("veridata.check", "ok")
        return {"status": "ok", "trace_id": _current_trace_id()}
