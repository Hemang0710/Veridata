# Spec 001 — Thin end-to-end slice

**Status:** Ready for plan review
**Scope target:** Weeks 1–2

## Specify (what and why)

### Goal
Prove the core pipe works end to end: a user can upload a CSV, ask one question
in plain English, and get back a correct answer plus the SQL that produced it.
No verification, no charts, no ambiguity handling yet; those come in later
specs. This slice de-risks everything downstream.

### User stories
- As a user, I can upload a CSV file and see that it loaded, with its columns
  listed.
- As a user, I can type a question in English and get an answer.
- As a user, I can see the exact SQL that was run to produce my answer.

### Acceptance criteria
- Given a valid CSV, when I upload it, then it loads into DuckDB and the
  response lists the detected columns and the row count.
- Given a loaded table, when I ask a question answerable by a single SQL query,
  then the system generates SQL, runs it read-only against DuckDB, and returns
  the result.
- The exact SQL executed is returned alongside every answer.
- Generated SQL is read-only; any write or DDL statement is rejected before
  execution.
- The LLM is sent only the schema and up to 5 sample rows, never the full
  dataset.
- On a handful of hand-written test questions against a sample CSV, the returned
  answers are correct.
- Every `/ask` request produces one OpenTelemetry trace with a span per step
  (schema build, model call, guard, execution), and model-call spans record the
  model, version, tokens, and latency.
- Every `/ask` request persists a run record keyed by the trace ID, including the
  question, schema shown, prompt, model + version, SQL, guard decision, row count
  after each step, and final answer.

### Out of scope (do not build yet)
- Result self-verification and confidence/abstention (spec 002).
- Ambiguity detection and clarifying questions (spec 003).
- Charts and visualizations.
- Database connectors beyond a local file; joins across multiple sources.
- Auth, multi-user, persistence of past sessions.

## Plan (how)

### Components
- `ingest`: read CSV into a DuckDB table; return schema + sample rows + row count.
- `schema`: build a compact schema summary (column names, types, 5 sample rows)
  for the prompt.
- `sql_agent`: given the schema summary + question, produce a single SQL
  statement via the LLM wrapper.
- `guard`: reject any non-SELECT statement before execution.
- `executor`: run the SQL read-only against DuckDB and return rows.
- `api`: FastAPI endpoints — `POST /upload`, `POST /ask`.
- `web`: minimal Next.js page — upload control, question box, answer + SQL view.
- `telemetry`: OpenTelemetry setup, trace-ID middleware, and per-step spans.
- `run_record`: persist the full per-question record keyed by trace ID.

### Data flow
CSV -> ingest -> DuckDB. Question -> (schema summary + question) -> sql_agent
-> guard -> executor -> { answer, sql } -> web.

### Key decisions
- DuckDB in-process; one table per uploaded file for this slice.
- LLM behind the provider-agnostic wrapper from day one.
- Read-only enforcement lives in `guard`, not in the prompt. Never trust the
  model for safety.

## Tasks
1. Project scaffold: repo, `CLAUDE.md`, Python + FastAPI backend, Next.js
   frontend, CI running lint + tests.
2. Observability foundation: OpenTelemetry SDK + exporter, trace-ID middleware,
   Sentry, and a trace viewer running locally. Do this before feature work.
3. `ingest` + `schema` with unit tests (load a sample CSV, assert columns and
   row count).
4. LLM wrapper (provider-agnostic) with a mockable interface for tests, emitting
   a model-call span with model, version, tokens, and latency.
5. `sql_agent`: prompt + parse to a single SQL string.
6. `guard`: SELECT-only validation, with tests for rejected statements.
7. `executor`: read-only DuckDB execution, with tests.
8. `run_record`: assemble and persist the per-question record keyed by trace ID,
   with a span per step and row counts after each step.
9. `POST /upload` and `POST /ask` endpoints, with the trace ID returned to the
   client.
10. Minimal frontend page wired to both endpoints, showing the answer, the SQL,
    and the trace ID.
11. A small set of hand-written question/answer test cases against a sample CSV
    (the seed of your eval set).