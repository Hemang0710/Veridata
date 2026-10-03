from pathlib import Path

from app.ingest import ingest_csv

SAMPLE = Path(__file__).parent / "data" / "sample.csv"


def test_ingest_detects_columns_and_row_count():
    result = ingest_csv(SAMPLE)

    assert [c.name for c in result.columns] == ["id", "name", "department", "salary"]
    assert result.row_count == 6

    types = {c.name: c.type.upper() for c in result.columns}
    assert "INT" in types["id"]
    assert types["name"] in ("VARCHAR", "TEXT", "STRING")
    assert any(t in types["salary"] for t in ("DOUBLE", "FLOAT", "DECIMAL"))
