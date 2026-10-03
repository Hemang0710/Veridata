"""Build a compact schema summary for the LLM prompt (task 3).

This is the only data content the model ever sees: column names, types, and up
to 5 sample rows — never the full dataset (CLAUDE.md architecture rule).
"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb
from opentelemetry import trace

from .ingest import Column, _safe_table, table_columns

tracer = trace.get_tracer("veridata")


@dataclass
class SchemaSummary:
    table: str
    columns: list[Column]
    sample_rows: list[dict]

    def to_prompt(self) -> str:
        cols = ", ".join(f"{c.name} ({c.type})" for c in self.columns)
        lines = [f"Table: {self.table}", f"Columns: {cols}", "Sample rows:"]
        for row in self.sample_rows:
            lines.append("  " + ", ".join(f"{k}={v}" for k, v in row.items()))
        return "\n".join(lines)


def build_schema_summary(
    con: duckdb.DuckDBPyConnection,
    table: str = "data",
    sample_limit: int = 5,
) -> SchemaSummary:
    """Column names + types and up to `sample_limit` sample rows for the prompt."""
    _safe_table(table)
    with tracer.start_as_current_span("schema.build_summary") as span:
        columns = table_columns(con, table)
        cur = con.execute(f"SELECT * FROM {table} LIMIT {int(sample_limit)}")
        names = [d[0] for d in cur.description]
        sample_rows = [dict(zip(names, r)) for r in cur.fetchall()]

        span.set_attribute("veridata.column_count", len(columns))
        span.set_attribute("veridata.sample_row_count", len(sample_rows))
        return SchemaSummary(table=table, columns=columns, sample_rows=sample_rows)
