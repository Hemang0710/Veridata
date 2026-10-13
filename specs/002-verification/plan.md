# Spec 002 — Implementation plan (for review)

Grounded in the spec-001 code on `feature/002-checks`. Read alongside `spec.md`.
Nothing here is built until this plan is reviewed (CLAUDE.md workflow).

## Shape of the change

Insert a verification stage after `run_query` in `answer_question`. Three new
single-responsibility modules mirror the spec's named components; the pipeline,
run record, `/ask` response, and eval seed are extended. No new dependencies.

```
executor -> QueryResult
          -> verifier.verify(checks -> [gate] -> judge) -> Verification
          -> fold into RunRecord + AskResult + /ask response
```

## New files

### `app/checks.py` — deterministic, pure, no model call
```python
@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str

def check_sql_executed(error: str | None) -> CheckResult      # passed = error is None
def check_result_shape(result: QueryResult) -> CheckResult    # fail: 0 rows, or single-row all-null aggregate
def check_consistency(primary: QueryResult, alt: QueryResult | None,
                      alt_error: str | None) -> CheckResult    # compares headline numbers
```
- `check_consistency` is **pure**: it only *compares*. Generating and running the
  alternate SQL happens in `verifier` and is passed in. Keeps checks model-free
  per the spec ("each a small pure function ... No model call").
- Headline number = first numeric cell of the first row. If either result has no
  numeric headline (e.g. answer is `"Carol"`), the check is **not comparable** →
  `passed=True, detail="no numeric headline to compare"` (feeds the `medium`
  mapping below). Real numeric mismatch beyond tolerance, or `alt_error` set →
  `passed=False`.

### `app/judge.py` — LLM-as-judge, mockable
```python
def judge_answer(llm: LLM, question: str, sql: str, result: QueryResult) -> CheckResult
```
- Prompt: question + SQL + a truncated result preview; asks whether the SQL and
  result actually answer the question. Requires first line `VERDICT: yes|no|unsure`.
- Lenient parse: find yes/no/unsure; **unparseable → unsure** (fail-safe).
- Returns `CheckResult(name="judge", passed=(verdict=="yes"), detail=reason)` plus
  the raw verdict so the mapper can distinguish `no` from `unsure`.
- Wrapped in a `judge.check` span; the model call itself already gets `llm.call`.

### `app/verifier.py` — orchestration + confidence mapping (one place)
```python
@dataclass
class Verification:
    confidence: str        # "high" | "medium" | "low"
    abstained: bool
    reason: str
    checks: list[CheckResult]   # deterministic checks + judge, uniform list

def verify(llm, con, table, question, sql, result, *, records_dir=None) -> Verification
def _map(checks, judge_verdict, consistency_comparable) -> tuple[str, bool, str]  # pure, unit-tested directly
```
- Order: run deterministic checks. **Gate:** if any deterministic check failed,
  skip the judge (no model call) → `low` + abstain. Else generate one alternate
  SQL (reworded question via `generate_sql`), **guard it**, run it, feed into
  `check_consistency`, then call `judge_answer`.
- `_map` is a pure function so task 3's high/medium/low/abstain tests need neither
  a DB nor an LLM.
- Span `verifier.run`; one short span per check.

**Confidence mapping (the whole table):**

| Deterministic checks | Judge | Consistency | → confidence | abstained |
|---|---|---|---|---|
| any failed | (skipped) | — | low | yes |
| all pass | no / unsure | — | low | yes |
| all pass | yes | not comparable | medium | no |
| all pass | yes | matched | high | no |

`reason` is assembled from the failing/weak checks (e.g. "consistency check: 6 vs
8"; "judge: result counts departments, not employees").

## Edited files

- **`app/pipeline.py`** — after `run_query`, wrap execution so an executor error
  becomes `check_sql_executed(error=...)` → a `low`+abstain `Verification` instead
  of a 500 (faithful to the spec's "SQL executed without error" check + abstain
  AC). Call `verify(...)`, set `record.verification = asdict(v)`, extend
  `AskResult` with `confidence`, `checks`, `abstained`, `reason`.
- **`app/run_record.py`** — add `verification: dict | None = None`. `asdict` already
  serializes it; no import of verifier (pipeline passes the dict).
- **`app/main.py`** — `/ask` response gains `confidence` and `checks` (and
  `abstained`/`reason`). Abstention still returns 200 with the answer, per spec.
- **`app/llm.py`** — extend `MockLLM` to accept `responses: list[str]` consumed in
  order (backward compatible: single `text=` still returns that text every call).
  Needed because verification adds 2 model calls per `/ask`.
- **`tests/test_eval_seed.py`** — add a verified-vs-baseline comparison (below).

## Tests (one per spec task)

- `tests/test_checks.py` — each check incl. failing cases: 0 rows, all-null
  aggregate, numeric mismatch, not-comparable, alt-error.
- `tests/test_judge.py` — yes / no / unsure / unparseable(→unsure) via `MockLLM`.
- `tests/test_verifier.py` — `_map` for all four rows of the table; one end-to-end
  `verify` over a tiny in-memory DuckDB + scripted `MockLLM`.
- `tests/test_pipeline.py` (extend) — verification lands in `AskResult` + run
  record; executor-error → abstain path.
- `tests/test_api.py` (extend) — `/ask` body has `confidence` + `checks`; add a
  scripted-`MockLLM` high-confidence case. Existing assertions still hold
  (abstain is still 200 with an answer).

## Eval extension (task 6)

Extend the seed test to report, over the cases, two rates (real model, still
skipped without a key):
- **baseline wrong-answer rate** = fraction of cases where `_contains` is False.
- **verified wrong-answer rate** = fraction of *presented* answers (not abstained,
  not `low`) that are wrong — verification's job is to withhold the wrong ones.

Print both and assert `verified <= baseline` (always holds; the number is the
artifact). Add 1–2 deliberately hard/ambiguous cases so the gap can be non-zero.

> `ponytail:` a richer wrong-answer corpus is the real lever here; this slice
> delivers the measurement mechanism, not a big labelled set. Graduate to the
> BIRD/Spider harness (CLAUDE.md) in a later spec.

## Decisions needing your sign-off

1. **Executor error → abstain (200) instead of 500.** Makes `check_sql_executed`
   a real check and matches the abstain AC, but changes spec-001's error
   behavior. Recommended; flagging because it's a behavior change.
2. **`MockLLM` gains sequential `responses`.** Smallest way to script the 3 model
   calls per `/ask` in tests. Alternative (prompt-routing mock) is more work.
3. **Cost:** verification adds 2 model calls per `/ask` (consistency alt-SQL +
   judge). Inherent to the spec's design; noting it.
4. **`medium` definition:** all deterministic pass + judge `yes` but the number
   couldn't be independently corroborated (string answers, no numeric headline).
   This is how high/medium/low stay distinct — confirm it matches your intent.
```
