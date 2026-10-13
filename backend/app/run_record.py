"""Per-question run record, keyed by trace ID (task 8).

One auditable record per /ask: question, schema shown, exact prompt, model +
version, generated SQL, guard decision, row count after each step, and final
answer. Persisted as one JSON file per trace ID so a bug report maps to a
single trace and a single record.

# ponytail: one JSON file per trace on local disk; swap persist() for a table
# when run records need querying or survive beyond a single machine.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

from opentelemetry import trace

tracer = trace.get_tracer("veridata")

_DEFAULT_DIR = Path(__file__).resolve().parent.parent / "run_records"


@dataclass
class RunRecord:
    trace_id: str
    question: str
    schema_shown: str  # the schema summary the model saw (never the full dataset)
    prompt: str  # exact prompt sent to the model
    model: str
    model_version: str
    sql: str | None
    guard_decision: str  # "allow" | "reject"
    guard_reason: str | None
    row_counts: dict[str, int] = field(default_factory=dict)  # per-step row counts
    answer: dict | None = None  # {"columns": [...], "rows": [...]}
    verification: dict | None = None  # asdict of the Verification (checks, confidence, ...)
    error: str | None = None


def _records_dir(records_dir: str | Path | None) -> Path:
    if records_dir is not None:
        return Path(records_dir)
    return Path(os.getenv("VERIDATA_RUN_RECORDS_DIR") or _DEFAULT_DIR)


def persist(record: RunRecord, records_dir: str | Path | None = None) -> Path:
    """Write the record as {trace_id}.json and return its path."""
    with tracer.start_as_current_span("run_record.persist") as span:
        directory = _records_dir(records_dir)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{record.trace_id}.json"
        path.write_text(json.dumps(asdict(record), indent=2, default=str), encoding="utf-8")
        span.set_attribute("veridata.run_record.path", str(path))
        return path
