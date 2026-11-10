"""Pure chart-typing for verified answers (spec 005 task 1).

The backend decides whether a result is chartable and which type fits; the
frontend only renders the returned spec (spec decision 1). Kept web- and
model-free so the rules live in one legible, unit-testable place.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass


@dataclass(frozen=True)
class ChartSpec:
    """The whole contract the frontend renders. Explicit so the two sides can't drift."""

    type: str  # "bar" | "line"
    labels: list[str]  # x-axis categories or dates
    values: list[float]  # y-axis numeric values
    x_title: str  # label column name
    y_title: str  # numeric column name


def _kind(values: list) -> str:
    """Classify a column from its non-null values: numeric | datetime | category | other."""
    present = [v for v in values if v is not None]
    if not present:
        return "other"
    # bool is an int subclass; a true/false column is not a measure.
    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in present):
        return "numeric"
    if all(isinstance(v, dt.date) for v in present):  # date and its subclass datetime
        return "datetime"
    if all(isinstance(v, str) for v in present):
        return "category"
    return "other"


def _label(v) -> str:
    if isinstance(v, dt.date):  # date / datetime -> ISO string
        return v.isoformat()
    return str(v)


def build_chart_spec(result: dict, confidence: str) -> ChartSpec | None:
    """Return a ChartSpec for a chartable 2-column result, else None.

    `result` is the answer dict {"columns": [...], "rows": [...]}. Charts only on a
    trusted answer: confidence must be "medium" or "high". An abstained answer always
    maps to "low" (verifier._map), so this one gate also covers abstain.

    Shape rules (bar and line only, per spec): one numeric column + one category
    column -> bar; one numeric column + one date/time column -> line. Everything
    else, including a scalar (one column), is not chartable -> None.
    """
    if confidence not in ("high", "medium"):
        return None

    columns = result.get("columns") or []
    rows = result.get("rows") or []
    if len(columns) != 2 or not rows:
        return None  # scalar / single value / any non-2-column shape is not chartable

    col_values = [[row[i] for row in rows] for i in range(2)]
    kinds = [_kind(v) for v in col_values]
    if "numeric" not in kinds:
        return None
    num_idx = kinds.index("numeric")
    lbl_idx = 1 - num_idx

    label_kind = kinds[lbl_idx]
    if label_kind == "category":
        chart_type = "bar"
    elif label_kind == "datetime":
        chart_type = "line"
    else:
        return None  # numeric+numeric, date+category, etc. -> not chartable

    # Drop rows with a null measure (can't plot a null bar) while keeping labels aligned.
    pairs = [
        (col_values[lbl_idx][r], col_values[num_idx][r])
        for r in range(len(rows))
        if col_values[num_idx][r] is not None
    ]
    return ChartSpec(
        type=chart_type,
        labels=[_label(label) for label, _ in pairs],
        values=[float(value) for _, value in pairs],
        x_title=columns[lbl_idx],
        y_title=columns[num_idx],
    )
