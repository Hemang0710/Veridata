"""Deterministic verification checks — pure, no model call (spec 002 task 1).

Each check is a small pure function returning a CheckResult(name, passed, detail).
They run before the LLM judge and gate it: if a cheap check already shows the
answer is untrustworthy, the verifier skips the expensive model call (spec key
decision). The alternate query for the consistency check is generated and run by
the verifier and passed in here — these functions never call a model themselves.
"""

from __future__ import annotations

from dataclasses import dataclass

from .executor import QueryResult

# The consistency check passes but could not actually corroborate the number
# (the answer isn't numeric). The verifier maps this to medium confidence.
CONSISTENCY_NOT_COMPARABLE = "no numeric headline to cross-check"


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str


def check_sql_executed(error: str | None) -> CheckResult:
    """Pass unless the primary query raised. `error` is the exception text, or None."""
    if error:
        return CheckResult("sql_executed", False, f"query failed: {error}")
    return CheckResult("sql_executed", True, "query executed without error")


def _all_null(result: QueryResult) -> bool:
    """A single-row result whose every cell is NULL — an empty aggregate as a row."""
    return len(result.rows) == 1 and all(cell is None for cell in result.rows[0])


def check_result_shape(result: QueryResult) -> CheckResult:
    """Fail on an unexpectedly empty result or an all-null single-row aggregate."""
    if result.row_count == 0:
        return CheckResult("result_shape", False, "result is empty (0 rows)")
    if _all_null(result):
        return CheckResult("result_shape", False, "aggregate is all-null (no rows matched)")
    return CheckResult("result_shape", True, f"{result.row_count} row(s)")


def _headline_number(result: QueryResult) -> float | None:
    """First numeric cell of the first row, or None if the answer isn't numeric.

    Bools are ints in Python but are not a headline number, so they're skipped.
    """
    if not result.rows:
        return None
    for cell in result.rows[0]:
        if isinstance(cell, bool):
            continue
        if isinstance(cell, (int, float)):
            return float(cell)
    return None


def check_consistency(
    primary: QueryResult,
    alt: QueryResult | None,
    alt_error: str | None,
    tolerance: float = 0.01,
) -> CheckResult:
    """Compare the primary result's headline number against an alternate query's.

    A mismatch beyond tolerance is a strong low-confidence signal. No numeric
    headline (e.g. the answer is a name) is not a failure — it passes as "not
    comparable" and the verifier downgrades it to medium.
    """
    if alt_error:
        return CheckResult("consistency", False, f"alternate query failed: {alt_error}")
    if alt is None:
        return CheckResult("consistency", False, "no alternate query produced")
    a = _headline_number(primary)
    b = _headline_number(alt)
    if a is None or b is None:
        return CheckResult("consistency", True, CONSISTENCY_NOT_COMPARABLE)
    if abs(a - b) <= tolerance:
        return CheckResult("consistency", True, f"headline numbers match ({a})")
    return CheckResult("consistency", False, f"headline numbers differ ({a} vs {b})")
