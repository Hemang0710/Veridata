import duckdb

from app.checks import (
    CONSISTENCY_COULD_NOT_CORROBORATE,
    CONSISTENCY_NOT_COMPARABLE,
    CheckResult,
)
from app.executor import run_query
from app.llm import MockLLM
from app.verifier import MEDIUM_REASON, _map, verify


def _c(name, passed, detail="x"):
    return CheckResult(name, passed, detail)


# --- pure confidence mapping (no DB, no LLM) ---


def test_map_deterministic_failure_is_low_and_abstains():
    conf, abstained, reason = _map([_c("sql_executed", True), _c("result_shape", False, "empty")])
    assert conf == "low" and abstained
    assert reason == "empty"


def test_map_consistency_failure_is_low():
    conf, abstained, _ = _map(
        [_c("sql_executed", True), _c("result_shape", True), _c("consistency", False, "6 vs 8")]
    )
    assert conf == "low" and abstained


def test_map_judge_no_is_low_and_abstains():
    conf, abstained, reason = _map(
        [
            _c("sql_executed", True),
            _c("result_shape", True),
            _c("consistency", True, "match (6.0)"),
            _c("judge", False, "no: counts departments not employees"),
        ]
    )
    assert conf == "low" and abstained
    assert reason == "no: counts departments not employees"


def test_map_judge_yes_not_comparable_is_medium_with_reason():
    conf, abstained, reason = _map(
        [
            _c("sql_executed", True),
            _c("result_shape", True),
            _c("consistency", True, CONSISTENCY_NOT_COMPARABLE),
            _c("judge", True, "yes"),
        ]
    )
    assert conf == "medium" and not abstained
    assert reason == MEDIUM_REASON


def test_map_judge_yes_could_not_corroborate_is_medium_not_abstain():
    conf, abstained, reason = _map(
        [
            _c("sql_executed", True),
            _c("result_shape", True),
            _c("consistency", True, f"{CONSISTENCY_COULD_NOT_CORROBORATE}: multiple statements"),
            _c("judge", True, "yes"),
        ]
    )
    assert conf == "medium" and not abstained
    assert reason.startswith(CONSISTENCY_COULD_NOT_CORROBORATE)


def test_map_judge_yes_matched_is_high():
    conf, abstained, _ = _map(
        [
            _c("sql_executed", True),
            _c("result_shape", True),
            _c("consistency", True, "headline numbers match (6.0)"),
            _c("judge", True, "yes"),
        ]
    )
    assert conf == "high" and not abstained


# --- end-to-end over a tiny in-memory DuckDB + scripted MockLLM ---


def _db():
    con = duckdb.connect()
    con.execute(
        "CREATE TABLE data AS SELECT * FROM (VALUES (1,'Eng'),(2,'Eng'),(3,'Sales')) t(id,dept)"
    )
    return con


def test_verify_end_to_end_high_confidence():
    con = _db()
    result = run_query(con, "SELECT count(*) AS n FROM data")  # -> 3
    llm = MockLLM(responses=["SELECT count(id) AS n FROM data", "VERDICT: yes looks right"])
    v = verify(con, "data", "how many rows?", "SELECT count(*) AS n FROM data", result, llm)
    assert v.confidence == "high" and not v.abstained
    assert [c.name for c in v.checks] == ["sql_executed", "result_shape", "consistency", "judge"]


def test_verify_consistency_mismatch_skips_judge_and_abstains():
    con = _db()
    result = run_query(con, "SELECT count(*) AS n FROM data")  # -> 3
    # alt query returns 2 -> mismatch -> judge is never called (no second response scripted)
    llm = MockLLM(responses=["SELECT count(*) AS n FROM data WHERE dept = 'Eng'"])
    v = verify(con, "data", "how many rows?", "SELECT count(*) AS n FROM data", result, llm)
    assert v.confidence == "low" and v.abstained
    assert "judge" not in [c.name for c in v.checks]


def test_verify_multistatement_alternate_is_sanitized_and_runs():
    # The reported bug: the alt query came back as several statements and the
    # guard rejected it, abstaining on everything. first_statement() now keeps
    # only the first, so the cross-check actually runs and corroborates -> high.
    con = _db()
    result = run_query(con, "SELECT count(*) AS n FROM data")  # -> 3
    llm = MockLLM(responses=["SELECT count(id) AS n FROM data;\nSELECT 0", "VERDICT: yes"])
    v = verify(con, "data", "how many rows?", "SELECT count(*) AS n FROM data", result, llm)
    assert v.confidence == "high" and not v.abstained


def test_verify_unrunnable_alternate_is_medium_not_low():
    # Alt SQL is a valid single SELECT (passes the guard) but hits a missing
    # table, so it errors at execution -> "could not corroborate" -> medium.
    # Must NOT abstain, and the judge still runs as the fallback trust signal.
    con = _db()
    result = run_query(con, "SELECT count(*) AS n FROM data")  # -> 3
    llm = MockLLM(responses=["SELECT count(*) AS n FROM nope", "VERDICT: yes"])
    v = verify(con, "data", "how many rows?", "SELECT count(*) AS n FROM data", result, llm)
    assert v.confidence == "medium" and not v.abstained
    assert "judge" in [c.name for c in v.checks]


def test_verify_executor_error_abstains_without_any_model_call():
    con = _db()
    # error set, result None -> sql_executed fails, nothing downstream runs.
    # MockLLM(responses=[]) raises if called, so this also proves no model call.
    llm = MockLLM(responses=[])
    v = verify(con, "data", "q", "SELECT bad", None, llm, error="Binder Error: no column bad")
    assert v.confidence == "low" and v.abstained
    assert [c.name for c in v.checks] == ["sql_executed"]
