"""Run validated SQL against DuckDB and return rows (task 7).

Read-only is guaranteed upstream by the guard (spec key decision: enforcement
lives in the guard, not here).
# ponytail: relies on the guard for read-only; open the DB with read_only=True
# once we move from in-memory to file-backed databases.
"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb
from opentelemetry import trace

tracer = trace.get_tracer("veridata")


@dataclass
class QueryResult:
    columns: list[str]
    rows: list[tuple]
    row_count: int


def run_query(con: duckdb.DuckDBPyConnection, sql: str) -> QueryResult:
    with tracer.start_as_current_span("executor.run") as span:
        cur = con.execute(sql)
        columns = [d[0] for d in cur.description]
        rows = cur.fetchall()
        span.set_attribute("veridata.row_count", len(rows))
        return QueryResult(columns=columns, rows=rows, row_count=len(rows))
