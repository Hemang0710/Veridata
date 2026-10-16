from app.executor import QueryResult
from app.judge import judge_answer
from app.llm import MockLLM

RESULT = QueryResult(columns=["n"], rows=[(6,)], row_count=1)


def _judge(text):
    return judge_answer(MockLLM(text), "how many employees?", "SELECT count(*) FROM data", RESULT)


def test_yes_passes():
    r = _judge("VERDICT: yes, counts all rows as asked")
    assert r.passed
    assert r.detail.startswith("yes:")


def test_no_fails():
    r = _judge("VERDICT: no, this counts departments not employees")
    assert not r.passed
    assert r.detail.startswith("no:")


def test_unsure_fails():
    assert not _judge("VERDICT: unsure, the filter is ambiguous").passed


def test_unparseable_is_unsure():
    r = _judge("I think it's probably fine but who knows")
    assert not r.passed
    assert r.detail.startswith("unsure:")


def test_no_is_not_matched_inside_another_word():
    # "none" / "not" must not be read as a "no" verdict
    assert _judge("VERDICT: yes — none of the rows are null, nothing is wrong").passed


def test_prompt_carries_question_sql_and_result():
    llm = MockLLM("VERDICT: yes ok")
    judge_answer(llm, "how many employees?", "SELECT count(*) FROM data", RESULT)
    assert "how many employees?" in llm.last_prompt
    assert "SELECT count(*) FROM data" in llm.last_prompt
    assert "6" in llm.last_prompt
