"""Load an uploaded CSV into DuckDB and report its detected schema (task 3).

One table per uploaded file, one in-process DuckDB connection.
# ponytail: single in-memory table per connection; add file-backed DBs and
# multi-table support when the slice needs more than one dataset at a time.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb
from opentelemetry import trace

tracer = trace.get_tracer("veridata")


@dataclass
class Column:
    name: str
    type: str


@dataclass
class IngestResult:
    con: duckdb.DuckDBPyConnection
    table: str
    columns: list[Column]
    row_count: int


def _safe_table(table: str) -> str:
    """Reject anything that isn't a bare identifier — table names are interpolated."""
    if not table.isidentifier():
        raise ValueError(f"invalid table name: {table!r}")
    return table


def table_columns(con: duckdb.DuckDBPyConnection, table: str) -> list[Column]:
    """Detected columns and DuckDB types for a table. Shared with the schema module."""
    rows = con.execute(f"DESCRIBE {_safe_table(table)}").fetchall()
    return [Column(name=r[0], type=r[1]) for r in rows]


def ingest_csv(
    csv_path: str | Path,
    con: duckdb.DuckDBPyConnection | None = None,
    table: str = "data",
) -> IngestResult:
    """Load a CSV into `table`, returning the connection, columns/types, and row count.

    DuckDB's read_csv_auto detects column types. Creates an in-memory connection
    if one isn't supplied so the caller (schema, executor) can reuse the same DB.
    """
    _safe_table(table)
    with tracer.start_as_current_span("ingest.load_csv") as span:
        con = con or duckdb.connect()
        con.execute(
            f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM read_csv_auto(?)",
            [str(csv_path)],
        )
        columns = table_columns(con, table)
        row_count = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]

        span.set_attribute("veridata.table", table)
        span.set_attribute("veridata.row_count", row_count)
        span.set_attribute("veridata.column_count", len(columns))
        return IngestResult(con=con, table=table, columns=columns, row_count=row_count)
