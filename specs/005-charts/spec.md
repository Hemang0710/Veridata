# Spec 005 — Charts

**Status:** Ready for plan review
**Scope target:** Visualize chartable results, on top of the verified answer.

## Specify (what and why)

### Goal
When an answer's result is a shape that reads better as a picture (a value per
category, a trend over time), show a chart beneath the answer. Charts are a
visual aid to an answer the system already produced and verified — never a
replacement for the trust signal. A single number or a name is not a chart and
stays as-is.

Decisions (made):
1. **The backend decides.** It inspects the result shape, decides whether it is
   chartable and which chart type fits, and returns a small chart spec. The
   frontend only renders what it is given (thin client, per the constitution).
2. **Un-chartable results get no chart.** A scalar, a single name, or a shape
   that doesn't map to a chart returns "not chartable" and the UI shows the
   answer as it does today.
3. **No chart on abstain.** A chart renders only when confidence is medium or
   high. An abstained / low-confidence answer shows no chart, so a visual never
   lends false authority to an answer the system doesn't trust.

### User stories
- As a user, when I ask something like "average salary by department," I see a
  bar chart of the result under the answer.
- As a user, I still see the confidence badge first; the chart is secondary.
- As a user, when the result isn't chartable, nothing weird happens — I just get
  the answer.
- As a user, when the answer is abstained, I see the abstain reason and no chart.

### Acceptance criteria
- `/ask` responses include an optional chart spec: either a renderable spec
  (type, labels, series/values, axis titles) or an explicit "not chartable".
- The backend chooses the chart type from the result shape: a category column
  plus a numeric column → bar; a date/time column plus a numeric column → line;
  otherwise not chartable (for this spec, bar and line only).
- A scalar result (one row, one numeric column) is "not chartable."
- A chart spec is produced only when confidence is medium or high; abstained /
  low answers carry no chart spec.
- The frontend renders the chart beneath the answer, with the confidence badge
  still the leading element; when there's no chart spec, the layout is unchanged.
- The chart logic is covered by unit tests on representative result shapes.

### Out of scope (do not build here)
- Pie, scatter, stacked, or multi-series charts (bar and line only for now).
- User-chosen chart types or chart editing.
- Charting the raw uploaded data outside of an answer.
- Downloading or exporting charts.

## Plan (how)

### Components
- `chart` (backend): a pure function `build_chart_spec(result, confidence)` →
  a ChartSpec or None. Inspects columns/rows, applies the type rules, and
  returns None when not chartable or when confidence is low/abstained.
- `pipeline` (extend): after verification, attach the chart spec to the response
  and the run record.
- API response (extend): add an optional `chart` field.
- `Chart` (frontend): renders a ChartSpec with a small, well-supported chart
  library; renders nothing when `chart` is absent.
- `AnswerCard` (extend): place the chart beneath the answer, below the badge.

### Data flow
… verifier → (answer, confidence) → build_chart_spec(result, confidence)
→ response.chart (spec or null) → AnswerCard renders Chart when present.

### Key decisions
- Chart typing lives in one pure backend function, so it's testable without a UI
  or a model and the rules are legible in one place.
- The ChartSpec is a small, explicit contract (type, labels, values, titles) so
  the frontend stays dumb and the two sides can't drift.
- Confidence gates charting in the backend, not the frontend, so the rule is
  enforced where the data is and can be unit-tested.

## Tasks
1. `chart.build_chart_spec`: the pure typing function + ChartSpec type, with unit
   tests covering bar (category+numeric), line (date+numeric), scalar
   (not chartable), low-confidence (no spec), and an un-mappable shape.
2. Extend the pipeline and run record to attach the chart spec; extend the `/ask`
   response with the optional `chart` field; update API tests.
3. Frontend `Chart` component rendering the spec with a charting library; renders
   nothing when absent.
4. Wire `Chart` into `AnswerCard` beneath the answer, badge still leading.
5. Manual check: upload `employees_test.csv`, ask "average salary by department"
   (expect a bar chart under a medium/high answer) and "what is the average age"
   (expect abstain, no chart).
