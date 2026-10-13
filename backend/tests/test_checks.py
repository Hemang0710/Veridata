from app.checks import (
    CONSISTENCY_NOT_COMPARABLE,
    check_consistency,
    check_result_shape,
    check_sql_executed,
)
from app.executor import QueryResult


def _qr(rows, columns=("n",)):
    return QueryResult(columns=list(columns), rows=rows, row_count=len(rows))


def test_sql_executed():
    assert check_sql_executed(None).passed
    failed = check_sql_executed("Binder Error: column foo does not exist")
    assert not failed.passed
    assert "foo" in failed.detail


def test_result_shape_fails_on_empty():
    assert not check_result_shape(_qr([])).passed


def test_result_shape_fails_on_all_null_aggregate():
    assert not check_result_shape(_qr([(None,)])).passed
    assert not check_result_shape(_qr([(None, None)], columns=("a", "b"))).passed


def test_result_shape_passes_on_normal_results():
    assert check_result_shape(_qr([(6,)])).passed
    assert check_result_shape(_qr([(1,), (2,)])).passed  # multi-row
    assert check_result_shape(_qr([(0,)])).passed  # zero is a real answer, not empty


def test_consistency_matches_within_tolerance():
    assert check_consistency(_qr([(6,)]), _qr([(6.004,)]), None).passed


def test_consistency_fails_on_mismatch():
    r = check_consistency(_qr([(6,)]), _qr([(8,)]), None)
    assert not r.passed
    assert "6" in r.detail and "8" in r.detail


def test_consistency_fails_on_alt_error_or_missing():
    assert not check_consistency(_qr([(6,)]), None, "Binder Error").passed
    assert not check_consistency(_qr([(6,)]), None, None).passed


def test_consistency_not_comparable_for_non_numeric_answer():
    r = check_consistency(_qr([("Carol",)]), _qr([("Carol",)]), None)
    assert r.passed
    assert r.detail == CONSISTENCY_NOT_COMPARABLE


def test_consistency_ignores_bools_as_headline():
    # a leading bool must not count as the headline number
    r = check_consistency(
        _qr([(True, 6)], columns=("flag", "n")), _qr([(False, 6)], columns=("flag", "n")), None
    )
    assert r.passed and "match" in r.detail
