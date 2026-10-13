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

    # verification ran and was folded into the result and the record
    assert result.confidence in {"high", "medium", "low"}
    assert record["verification"]["confidence"] == result.confidence
    assert [c["name"] for c in record["verification"]["checks"]][:3] == [
        "sql_executed",
        "result_shape",
        "consistency",
    ]


def test_guard_rejection_still_persists_record(tmp_path):
    con = _con()
    llm = MockLLM("DROP TABLE data")
    with pytest.raises(PipelineRejected) as exc:
        answer_question(con, "data", "delete everything", llm, records_dir=tmp_path)

    record = json.loads((tmp_path / f"{exc.value.trace_id}.json").read_text())
    assert record["guard_decision"] == "reject"
    assert record["answer"] is None
    assert record["sql"] == "DROP TABLE data"
    assert record["verification"] is None  # guard rejects before verification runs


def test_high_confidence_with_scripted_verify_llm(tmp_path):
    con = _con()
    primary = MockLLM("SELECT count(*) AS n FROM data")
    verify_llm = MockLLM(responses=["SELECT count(*) AS n FROM data", "VERDICT: yes correct"])
    result = answer_question(
        con, "data", "How many rows?", primary, verify_llm=verify_llm, records_dir=tmp_path
    )
    assert result.confidence == "high" and not result.abstained
    assert [c["name"] for c in result.checks] == [
        "sql_executed",
        "result_shape",
        "consistency",
        "judge",
    ]


def test_executor_error_abstains_instead_of_raising(tmp_path):
    con = _con()
    # a valid SELECT referencing an unknown column fails at execution, not the guard
    llm = MockLLM("SELECT nonexistent_col FROM data")
    result = answer_question(con, "data", "bad query", llm, records_dir=tmp_path)

    assert result.confidence == "low" and result.abstained
    assert result.answer == {"columns": [], "rows": []}
    record = json.loads((tmp_path / f"{result.trace_id}.json").read_text())
    assert record["error"]
    assert record["verification"]["abstained"] is True
    assert [c["name"] for c in record["verification"]["checks"]] == ["sql_executed"]
