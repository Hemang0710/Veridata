from pathlib import Path

from app.ingest import ingest_csv
from app.schema import build_schema_summary

SAMPLE = Path(__file__).parent / "data" / "sample.csv"


def test_schema_summary_caps_samples_and_renders_prompt():
    result = ingest_csv(SAMPLE)
    summary = build_schema_summary(result.con, result.table)

    assert [c.name for c in summary.columns] == ["id", "name", "department", "salary"]
    assert len(summary.sample_rows) == 5  # capped though the CSV has 6 rows

    prompt = summary.to_prompt()
    assert result.table in prompt
    for name in ["id", "name", "department", "salary"]:
        assert name in prompt
