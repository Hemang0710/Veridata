import datetime as dt

from app.chart import ChartSpec, build_chart_spec


def _result(columns, rows):
    return {"columns": list(columns), "rows": rows}


def test_bar_category_plus_numeric():
    spec = build_chart_spec(
        _result(["department", "avg_salary"], [("Eng", 120.0), ("Sales", 95.0)]),
        "high",
    )
    assert spec == ChartSpec(
        type="bar",
        labels=["Eng", "Sales"],
        values=[120.0, 95.0],
        x_title="department",
        y_title="avg_salary",
    )


def test_line_date_plus_numeric():
    spec = build_chart_spec(
        _result(["month", "revenue"], [(dt.date(2026, 1, 1), 10), (dt.date(2026, 2, 1), 14)]),
        "medium",
    )
    assert spec is not None
    assert spec.type == "line"
    assert spec.labels == ["2026-01-01", "2026-02-01"]
    assert spec.values == [10.0, 14.0]
    assert (spec.x_title, spec.y_title) == ("month", "revenue")


def test_scalar_is_not_chartable():
    # one row, one numeric column -> a single number, not a chart
    assert build_chart_spec(_result(["avg_age"], [(41.5,)]), "high") is None


def test_low_confidence_never_charts():
    # A perfectly chartable bar shape, but a low/abstained answer carries no chart.
    chartable = _result(["department", "avg_salary"], [("Eng", 120.0), ("Sales", 95.0)])
    assert build_chart_spec(chartable, "low") is None


def test_unmappable_shapes_are_not_chartable():
    # two numeric columns -> no category/date axis
    assert build_chart_spec(_result(["a", "b"], [(1, 2), (3, 4)]), "high") is None
    # two category columns -> no measure
    assert build_chart_spec(_result(["a", "b"], [("x", "y")]), "high") is None
    # three columns -> bar/line only
    assert build_chart_spec(_result(["d", "x", "y"], [("Eng", 1, 2)]), "high") is None


def test_null_measures_are_skipped():
    spec = build_chart_spec(
        _result(["dept", "total"], [("Eng", 5), ("Sales", None), ("Ops", 7)]),
        "high",
    )
    assert spec.labels == ["Eng", "Ops"]
    assert spec.values == [5.0, 7.0]
