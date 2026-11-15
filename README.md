# Veridata

**An AI data analyst that verifies its own answers.** Upload a CSV, ask in plain
English, and get back the answer, the SQL behind it, a confidence level, an
*abstain-when-unsure* signal, and a chart when the result is chartable.

![Veridata abstaining on an unanswerable question](docs/screenshot-abstain.png)

> *Placeholder — add `docs/screenshot-abstain.png` (the "average age" abstain case below makes a good one).*

---

## Why it exists

Generating SQL from a question is a solved problem; trusting the result is not.
Text-to-SQL tools hand back a confident number and a chart with no signal about
whether that number is right — and on realistic, messy data they are wrong often
enough that "looks plausible" is not good enough.

Veridata's job is the second half: after it writes and runs a query, it checks
its own result and either attaches a confidence level or **abstains** and says
why, rather than presenting a shaky number as fact.

A concrete example, run against an employee dataset that has a `hire_date` but no
birth date:

> **Q: "What is the average age of employees?"**
> Veridata writes plausible SQL, computes `6.75`, then **abstains** — the judge
> notes the query measured *tenure from hire_date*, not age, so it does not
> answer the question asked.

The number was computable. It just wasn't the answer. That gap is the product.

## Features

- **Self-verification before display.** Every answer passes deterministic checks
  (SQL executed, result shape is sane, a differently-phrased cross-check query
  agrees on the headline number), then an LLM-as-judge decides whether the SQL
  and result actually answer the question.
- **Confidence + abstention.** Each answer carries `high` / `medium` / `low`
  confidence and a one-line reason; when it can't be trusted the response
  abstains instead of asserting.
- **Fully auditable.** Every answer ships with its SQL, the exact checks that ran,
  and a trace ID. A per-question run record (question, schema shown, exact prompt,
  model + version, generated SQL, guard decision, row counts, verification) is
  persisted and keyed by that trace ID.
- **Read-only by construction.** Model-generated SQL is passed through a guard
  that permits only a single read-only `SELECT`/`WITH` and fails closed.
- **Charts when it makes sense.** A trusted 2-column result becomes a bar chart
  (category + number) or line chart (date + number); scalars and untrusted
  answers get no chart.
- **Provider-agnostic.** Business logic talks to an `LLM` interface, not a vendor
  SDK — Anthropic or any OpenAI-compatible endpoint (Groq, Gemini, OpenRouter, …).
- **Instrumented end to end.** OpenTelemetry spans per pipeline step (GenAI
  semantic conventions) exported to Langfuse, plus Sentry for errors.

## Live demo

- **Frontend:** https://veridata-tawny.vercel.app
- **Backend API:** https://veridata-o5ey.onrender.com

> The backend runs on a free tier that sleeps when idle. The **first request may
> take ~1 minute** while it wakes up; subsequent requests are fast.

## How it works

```
  CSV upload
      │
      ▼
 ┌─────────┐   ┌──────────┐   ┌───────────┐   ┌──────────────────┐   ┌──────────┐
 │ ingest  │──▶│  schema  │──▶│ SQL agent │──▶│ read-only guard  │──▶│ executor │
 │ (DuckDB)│   │ cols +   │   │  (LLM)    │   │ SELECT/WITH only │   │ (DuckDB, │
 │         │   │ ≤5 rows  │   │           │   │ fails closed     │   │ read-only)│
 └─────────┘   └──────────┘   └───────────┘   └──────────────────┘   └────┬─────┘
                                                                           │ result
                                                                           ▼
                            ┌───────────────────────────────────────────────────┐
                            │                  verification                      │
                            │  deterministic checks (no model call):             │
                            │    sql_executed → result_shape → consistency       │
                            │      (re-ask differently, compare headline number) │
                            │                     │ gate                          │
                            │                     ▼                               │
                            │  LLM-as-judge: does this answer the question?       │
                            │                     │                               │
                            │                     ▼                               │
                            │        confidence (high/med/low) + abstain         │
                            └───────────────────────────┬───────────────────────┘
                                                         ▼
                                          answer + SQL + checks + chart
                                        (+ persisted run record, keyed by trace id)
```

The cheap deterministic checks run first and **gate** the expensive model calls:
if a free check already shows the answer is untrustworthy, neither the
cross-check query nor the judge is spent. The judge is advisory — the guard is
the only thing that authorizes execution.

## Tech stack

Read from the code, not aspirational:

| Layer | What's used |
|-------|-------------|
| Backend API | Python 3.12, FastAPI, Uvicorn |
| Data engine | DuckDB (`read_csv_auto`, read-only query execution) |
| LLM access | Provider-agnostic `LLM` wrapper — `AnthropicLLM` + `OpenAICompatibleLLM` (any OpenAI-compatible chat API via `httpx`); `MockLLM` for tests |
| Verification | Deterministic checks (pure Python) + LLM-as-judge |
| Observability | OpenTelemetry (GenAI semantic conventions) → Langfuse over OTLP/HTTP; Sentry for errors; JSON run record per trace ID |
| Frontend | Next.js 14 (App Router) + React 18, TypeScript, Recharts |
| Tests | pytest (backend); `node --test` (frontend) |
| Dev tooling | ruff + black; GitHub Actions CI |
| Process | spec-driven development (`specs/NNN-feature-name/`) |

## Getting started

**Prerequisites:** Python 3.12+, Node 20+.

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env             # then fill in the values below
uvicorn app.main:app --reload    # serves on http://localhost:8000
```

Environment variables (see `backend/.env.example` — placeholders, never commit real keys):

| Variable | Purpose |
|----------|---------|
| `LLM_PROVIDER` | `anthropic` (default) or `openai` for any OpenAI-compatible API |
| `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL` | Anthropic key; model defaults to `claude-opus-4-8` |
| `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` | Used when `LLM_PROVIDER=openai` |
| `VERIDATA_VERIFY_MODEL` | Cheaper model for verification (defaults to Haiku on Anthropic) |
| `LANGFUSE_BASE_URL` / `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` | OTLP trace export (optional — app boots without it) |
| `SENTRY_DSN` | Error tracking (optional) |
| `CORS_ALLOW_ORIGINS` | Allowed frontend origin(s); defaults to `http://localhost:3000` |
| `VERIDATA_RUN_RECORDS_DIR` | Where run records are written (defaults to `backend/run_records`) |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase anon (public) key |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service-role key (server-only — never expose to the browser) |
| `SUPABASE_JWT_SECRET` | Secret used to verify Supabase access tokens (server-only) |

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local   # set NEXT_PUBLIC_API_BASE_URL if not localhost:8000
npm run dev                         # serves on http://localhost:3000
```

| Variable | Purpose |
|----------|---------|
| `NEXT_PUBLIC_API_BASE_URL` | Backend base URL (defaults to `http://localhost:8000`) |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL (client-side auth) |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon (public) key (client-side auth) |

### API

- `GET /health` — liveness + current trace ID
- `POST /upload` — multipart CSV; returns detected columns and row count
- `POST /ask` — `{ "question": "..." }`; returns answer, SQL, confidence,
  `abstained`, reason, checks, chart, and trace ID

## Running tests

```bash
# Backend — runs offline against MockLLM, no API key needed
cd backend && pytest -q

# Frontend
cd frontend && npm test
```

The backend unit tests run fully offline on a mock LLM. The **eval-seed cases hit
the real model and auto-skip** when no key (`LLM_API_KEY` / `ANTHROPIC_API_KEY`)
is configured, so CI stays offline and free. CI (`.github/workflows/ci.yml`) runs
ruff + black + pytest for the backend and lint + build for the frontend.

## Project structure

```
Veridata/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app: /health, /upload, /ask; CORS, trace-id header
│   │   ├── pipeline.py      # wires schema → agent → guard → executor → verifier → record
│   │   ├── ingest.py        # load CSV into DuckDB, report detected schema
│   │   ├── schema.py        # compact schema summary (cols + ≤5 sample rows) for the prompt
│   │   ├── sql_agent.py     # NL question → single SQL statement via the LLM
│   │   ├── guard.py         # read-only SELECT/WITH guard; fails closed
│   │   ├── executor.py      # run the guarded query against DuckDB
│   │   ├── checks.py        # deterministic checks (sql_executed, result_shape, consistency)
│   │   ├── judge.py         # LLM-as-judge verdict (advisory)
│   │   ├── verifier.py      # orchestrate checks → judge → confidence + abstain
│   │   ├── chart.py         # pure chart-typing (bar/line) for trusted results
│   │   ├── llm.py           # provider-agnostic LLM wrapper (Anthropic / OpenAI-compat / Mock)
│   │   ├── run_record.py    # per-question audit record, one JSON per trace ID
│   │   └── telemetry.py     # OpenTelemetry → Langfuse, Sentry init
│   ├── tests/               # pytest: unit (offline) + eval seed (skips without key)
│   ├── scripts/             # verify_probe.py and sample data
│   └── pyproject.toml
├── frontend/
│   ├── app/                 # Next.js App Router (layout, page)
│   ├── components/          # UploadPanel, QuestionBox, AnswerCard, Chart
│   ├── lib/api.ts           # typed client for /upload and /ask
│   └── package.json
├── specs/                   # spec-driven dev: 001 slice, 002 verification, 004 frontend,
│                            #   005 charts, 006 deploy
├── render.yaml              # backend deploy blueprint (Render)
├── CLAUDE.md                # project constitution / engineering rules
├── PRD.md
└── LICENSE
```

## Evaluation

**Honest status:** the verification mechanism is demonstrated working end to end.
It abstains on questions it cannot truthfully answer (the "average age" → tenure
case above) and trusts answers that are correct — verified manually via
`backend/scripts/verify_probe.py` (results in `backend/verify_probe_results.md`)
and by the seeded eval cases in `backend/tests/test_eval_seed.py`.

What is **not** yet done: a formally measured wrong-answer-reduction rate over a
larger, labelled adversarial set. The current seed set is small (a handful of
hand-written question → expected-answer cases), and the comparison harness
(`test_verification_lowers_wrong_answer_rate`) establishes the *measurement
mechanism* — baseline-wrong vs. presented-wrong — rather than a headline number.
**No reduction percentage is claimed yet.** Growing that labelled corpus is the
real lever and is in progress.

## Roadmap & known limitations

- **Larger eval set.** Graduate the seed cases to a BIRD/Spider-style harness and
  report a measured wrong-answer-reduction rate.
- **Clarifying questions.** Ambiguity detection (ask instead of guessing) is
  specified but not yet built.
- **Single dataset.** One in-memory dataset is held per backend process; no
  multi-upload, multi-table, or multi-user support.
- **Run records are ephemeral.** They're written to local disk and do not survive
  a restart (e.g. on the free-tier host).
- **Charts are bar/line only.** Other result shapes render as a table.

## License

MIT — see [LICENSE](LICENSE).
```
