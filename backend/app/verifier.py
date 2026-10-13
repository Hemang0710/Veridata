"""Orchestrate checks then judge, map to a confidence level (spec 002 task 3).

The one place the confidence rules live, so they stay legible and testable
(spec key decision). Cheap deterministic checks run first and cascade-gate the
model calls: if a free check already shows the answer is untrustworthy, neither
the consistency alt-query nor the judge is spent.

Kept independent of the web layer (CLAUDE.md): it imports the agent core, never
FastAPI. Persistence and the API response are the pipeline's job, not this.
"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb
from opentelemetry import trace

from .checks import (
    CONSISTENCY_NOT_COMPARABLE,
    CheckResult,
    check_consistency,
    check_result_shape,
    check_sql_executed,
)
from .executor import QueryResult, run_query
from .guard import guard_sql
from .judge import judge_answer
from .llm import LLM
from .schema import build_schema_summary
from .sql_agent import generate_sql

tracer = trace.get_tracer("veridata")

MEDIUM_REASON = "answer is non-numeric, could not cross-check"


@dataclass
class Verification:
    confidence: str  # "high" | "medium" | "low"
    abstained: bool
    reason: str
    checks: list[CheckResult]


def _run_check(name: str, fn) -> CheckResult:
    with tracer.start_as_current_span(f"check.{name}") as span:
        c = fn()
        span.set_attribute("veridata.check.passed", c.passed)
        span.set_attribute("veridata.check.detail", c.detail)
        return c


def _run_alternate(
    con: duckdb.DuckDBPyConnection, table: str, question: str, llm: LLM
) -> tuple[QueryResult | None, str | None]:
    """Generate a differently-phrased query for the same question, guard and run it.

    Best-effort: a failed cross-check must never crash the real answer's
    verification, so any failure (bad SQL, guard rejection, execution error) is
    returned as an error string and becomes a failed consistency signal.
    # ponytail: broad except is intentional here — the alt query is advisory.
    """
    try:
        schema = build_schema_summary(con, table)
        reworded = f"{question}\n(Answer this a different way as a cross-check.)"
        alt_sql = guard_sql(generate_sql(llm, schema, reworded).sql)
        return run_query(con, alt_sql), None
    except Exception as exc:  # noqa: BLE001 — advisory path, see docstring
        return None, str(exc)


def _map(checks: list[CheckResult]) -> tuple[str, bool, str]:
    """Pure confidence mapping. See the table in spec 002 plan.md."""
    by_name = {c.name: c for c in checks}
    for name in ("sql_executed", "result_shape", "consistency"):
        c = by_name.get(name)
        if c and not c.passed:
            return "low", True, c.detail
    judge = by_name.get("judge")
    if judge and not judge.passed:
        return "low", True, judge.detail
    consistency = by_name.get("consistency")
    if consistency is not None and consistency.detail == CONSISTENCY_NOT_COMPARABLE:
        return "medium", False, MEDIUM_REASON
    return "high", False, "all checks passed"


def verify(
    con: duckdb.DuckDBPyConnection,
    table: str,
    question: str,
    sql: str,
    result: QueryResult | None,
    llm: LLM,
    error: str | None = None,
) -> Verification:
    """Run checks (gating the model calls), then map to confidence + abstain.

    `error` is the primary query's execution error, or None. When it's set,
    `result` may be None: sql_executed fails and nothing downstream runs.
    """
    with tracer.start_as_current_span("verifier.run") as span:
        checks: list[CheckResult] = [_run_check("sql_executed", lambda: check_sql_executed(error))]
        if checks[0].passed:
            shape = _run_check("result_shape", lambda: check_result_shape(result))
            checks.append(shape)
            if shape.passed:
                alt, alt_error = _run_alternate(con, table, question, llm)
                consistency = _run_check(
                    "consistency", lambda: check_consistency(result, alt, alt_error)
                )
                checks.append(consistency)
                if consistency.passed:
                    checks.append(judge_answer(llm, question, sql, result))

        confidence, abstained, reason = _map(checks)
        span.set_attribute("veridata.confidence", confidence)
        span.set_attribute("veridata.abstained", abstained)
        return Verification(
            confidence=confidence, abstained=abstained, reason=reason, checks=checks
        )
