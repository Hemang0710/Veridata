"""Wire the full pipe: schema -> sql_agent -> guard -> executor (task 8/9).

Web-independent so the agent core stays testable and swappable (CLAUDE.md).
Opens one parent span per question; its trace ID keys the run record. Assembles
and persists the run record on every path, including guard rejection.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb
from opentelemetry import trace

from .executor import run_query
from .guard import GuardRejection, guard_sql
from .llm import LLM
from .run_record import RunRecord, persist
from .schema import build_schema_summary
from .sql_agent import generate_sql

tracer = trace.get_tracer("veridata")


@dataclass
class AskResult:
    trace_id: str
    sql: str
    answer: dict  # {"columns": [...], "rows": [...]}


class PipelineRejected(Exception):
    """The guard rejected the generated SQL. The run record is still persisted."""

    def __init__(self, trace_id: str, sql: str, reason: str) -> None:
        super().__init__(reason)
        self.trace_id = trace_id
        self.sql = sql
        self.reason = reason


def _trace_id() -> str:
    ctx = trace.get_current_span().get_span_context()
    return format(ctx.trace_id, "032x")


def answer_question(
    con: duckdb.DuckDBPyConnection,
    table: str,
    question: str,
    llm: LLM,
    records_dir: str | Path | None = None,
) -> AskResult:
    with tracer.start_as_current_span("pipeline.run") as span:
        trace_id = _trace_id()
        span.set_attribute("veridata.question", question)

        schema = build_schema_summary(con, table)
        agent = generate_sql(llm, schema, question)
        row_counts = {"sample_rows": len(schema.sample_rows)}

        record = RunRecord(
            trace_id=trace_id,
            question=question,
            schema_shown=schema.to_prompt(),
            prompt=agent.prompt,
            model=agent.response.model,
            model_version=agent.response.version,
            sql=agent.sql,
            guard_decision="allow",
            guard_reason=None,
            row_counts=row_counts,
        )

        try:
            safe_sql = guard_sql(agent.sql)
        except GuardRejection as exc:
            record.guard_decision = "reject"
            record.guard_reason = str(exc)
            record.error = str(exc)
            persist(record, records_dir)
            raise PipelineRejected(trace_id, agent.sql, str(exc)) from exc

        result = run_query(con, safe_sql)
        row_counts["result_rows"] = result.row_count
        answer = {"columns": result.columns, "rows": result.rows}
        record.sql = safe_sql
        record.answer = answer
        persist(record, records_dir)

        return AskResult(trace_id=trace_id, sql=safe_sql, answer=answer)
