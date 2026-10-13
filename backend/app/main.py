"""Veridata FastAPI app: observability foundation (task 2)."""

from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()  # before telemetry reads the environment

import os  # noqa: E402
import tempfile  # noqa: E402

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile  # noqa: E402
from opentelemetry import trace  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from .ingest import IngestResult, ingest_csv  # noqa: E402
from .llm import DEFAULT_VERIFY_MODEL, LLM, AnthropicLLM  # noqa: E402
from .pipeline import PipelineRejected, answer_question  # noqa: E402
from .telemetry import init_telemetry  # noqa: E402

app = FastAPI(title="Veridata")
init_telemetry(app)

tracer = trace.get_tracer("veridata")

# ponytail: single current dataset held in process; add dataset IDs + a registry
# when multi-upload or multi-user matters (out of scope for this slice).
_dataset: IngestResult | None = None

_llm: LLM | None = None
_verify_llm: LLM | None = None


def get_llm() -> LLM:
    """The model behind /ask. A FastAPI dependency so tests can override it."""
    global _llm
    if _llm is None:
        _llm = AnthropicLLM()
    return _llm


def get_verify_llm() -> LLM:
    """Cheaper model for verification (consistency + judge). Overridable in tests."""
    global _verify_llm
    if _verify_llm is None:
        _verify_llm = AnthropicLLM(model=os.getenv("VERIDATA_VERIFY_MODEL") or DEFAULT_VERIFY_MODEL)
    return _verify_llm


class AskBody(BaseModel):
    question: str


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


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    """Load a CSV into DuckDB; return the detected columns and row count."""
    global _dataset
    suffix = os.path.splitext(file.filename or "")[1] or ".csv"
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        tmp.write(await file.read())
        tmp.close()
        _dataset = ingest_csv(tmp.name)  # table lives in memory after load
    finally:
        os.unlink(tmp.name)
    return {
        "table": _dataset.table,
        "columns": [{"name": c.name, "type": c.type} for c in _dataset.columns],
        "row_count": _dataset.row_count,
    }


@app.post("/ask")
def ask(
    body: AskBody,
    llm: LLM = Depends(get_llm),
    verify_llm: LLM = Depends(get_verify_llm),
):
    """Run the pipe over a question; return the answer, SQL, verification, and trace ID.

    A low-confidence / abstained answer is still a 200 with the reason — only the
    guard rejects (400). The judge is advisory, never a gate.
    """
    if _dataset is None:
        raise HTTPException(status_code=400, detail="Upload a CSV first.")
    try:
        result = answer_question(
            _dataset.con, _dataset.table, body.question, llm, verify_llm=verify_llm
        )
    except PipelineRejected as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"SQL rejected by guard: {exc.reason}",
                "sql": exc.sql,
                "trace_id": exc.trace_id,
            },
        ) from exc
    return {
        "answer": result.answer,
        "sql": result.sql,
        "confidence": result.confidence,
        "abstained": result.abstained,
        "reason": result.reason,
        "checks": result.checks,
        "trace_id": result.trace_id,
    }
