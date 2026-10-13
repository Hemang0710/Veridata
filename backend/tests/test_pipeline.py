import json

import duckdb
import pytest

from app.ingest import ingest_csv
from app.llm import MockLLM
from app.pipeline import PipelineRejected, answer_question

SAMPLE = "tests/data/sample.csv"


def _con():
    return ingest_csv(SAMPLE, con=duckdb.connect()).con


def test_answer_question_persists_record_and_returns_answer(tmp_path):
    con = _con()
    llm = MockLLM("SELECT count(*) AS n FROM data")
    result = answer_question(con, "data", "How many rows?", llm, records_dir=tmp_path)

    assert result.sql == "SELECT count(*) AS n FROM data"
    assert result.answer["columns"] == ["n"]
    assert result.answer["rows"] == [(6,)]

    record = json.loads((tmp_path / f"{result.trace_id}.json").read_text())
    assert record["question"] == "How many rows?"
    assert record["guard_decision"] == "allow"
    assert record["model"] == "mock-model"
    assert record["row_counts"]["result_rows"] == 1
    assert "Sample rows" in record["schema_shown"]  # schema was captured


def test_guard_rejection_still_persists_record(tmp_path):
    con = _con()
    llm = MockLLM("DROP TABLE data")
    with pytest.raises(PipelineRejected) as exc:
        answer_question(con, "data", "delete everything", llm, records_dir=tmp_path)

    record = json.loads((tmp_path / f"{exc.value.trace_id}.json").read_text())
    assert record["guard_decision"] == "reject"
    assert record["answer"] is None
    assert record["sql"] == "DROP TABLE data"
