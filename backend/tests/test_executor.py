from pathlib import Path

from app.ingest import ingest_csv
from app.executor import run_query

SAMPLE = Path(__file__).parent / "data" / "sample.csv"


def test_run_query_returns_rows_and_columns():
    con = ingest_csv(SAMPLE).con

    total = run_query(con, "SELECT count(*) AS n FROM data")
    assert total.columns == ["n"]
    assert total.rows == [(6,)]

    sales = run_query(
        con, "SELECT name FROM data WHERE department = 'Sales' ORDER BY name"
    )
    assert sales.rows == [("Bob",), ("Eve",)]
    assert sales.row_count == 2
