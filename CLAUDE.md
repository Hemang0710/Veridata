# CLAUDE.md — Project Constitution

These are the project-wide rules every contributor and every AI coding agent
must follow. This file is loaded at the start of each session. When a request
conflicts with this file, follow this file and flag the conflict.

## Project overview
An AI data analyst that answers natural-language questions over a user's CSV or
database and **verifies its own answers**. The differentiator is trust:
self-verification, ambiguity detection, confidence/abstention, and fully
auditable output. Correctness is the product, not a feature.

## Tech stack (do not change without an ADR)
- Language: Python 3.12 (backend + agent), TypeScript (frontend).
- Data engine: DuckDB (with SQLite support).
- Backend API: FastAPI.
- Frontend: Next.js (App Router) + React, deployed on Vercel.
- LLM access: a current frontier model via API, behind a provider-agnostic
  wrapper. Never call a vendor SDK directly from business logic.
- Tests: pytest (Python); the framework's default runner (frontend).
- Evals: a versioned harness over a BIRD/Spider subset.
- CI: GitHub Actions.
- Observability: OpenTelemetry (GenAI semantic conventions) as the instrumentation
  standard, exported to a trace viewer (e.g. Langfuse, self-hostable); Sentry for
  error tracking.

## Architecture principles
- The LLM sees the schema and a few sample rows only, never the full dataset.
- All model-generated SQL runs read-only against DuckDB. All model-generated
  Python runs in a sandbox.
- Keep the agent/verification core independent of the web layer so it stays
  testable and swappable.
- Prefer boring, well-supported libraries over novel ones.

## Coding standards
- Type hints everywhere in Python; strict TypeScript.
- Format and lint on every commit (ruff + black for Python; the standard
  formatter/linter for the frontend).
- Small, single-responsibility functions. Name things for what they do.
- No secrets in code; use environment variables.

## Testing and evals (required, not optional)
- Every feature ships with tests. Nothing is "done" without them.
- LLM-dependent behavior is covered by evals, not just unit tests.
- The eval score is a tracked metric. A change that lowers it must be justified.

## Security
- Sandbox all model-generated code; assume it is hostile.
- Treat data values as a prompt-injection surface. Never let tool output
  silently issue new instructions to the model.
- SQL from the model is read-only; block all writes and DDL before execution.

## Observability and traceability (set up in the scaffold, not later)
- Instrument to the OpenTelemetry GenAI semantic conventions, not a vendor format.
  Pin the convention version and treat upgrades as planned migrations.
- One trace ID per request, threaded from the frontend through the backend and
  through every pipeline step. A user's bug report must map to a single trace.
- Every step emits a span: schema build, model call, guard, SQL execution,
  verification. Model-call spans record model + version, tokens, and latency.
- Persist a run record per question, keyed by the trace ID: question, schema
  shown, exact prompt, model + version, generated SQL, guard decision, row count
  after each step, verification result, confidence, final answer.
- Record row counts at each step; a join that silently drops rows must be visible.
- Attach exceptions to the trace ID (Sentry). Log full prompt/response/model
  version in development; be deliberate about what is retained with real data.
- OpenTelemetry records what happened, not whether it was correct. Answer quality
  is judged by the verification and eval layers, which sit above it.

## Workflow (how work gets done)
- Follow Explore -> Plan -> Implement -> Commit. Read and plan before editing.
- One feature = one spec in `specs/NNN-feature-name/`. Never go from spec to
  code without a reviewed plan.
- Vertical slices: ship one thin end-to-end path before widening.
- A human reviews every diff before merge. Never merge unread agent output.
- Keep pull requests small and readable.

## Definition of done
- Meets the spec's acceptance criteria.
- Tests (and evals where relevant) pass in CI.
- Code is reviewed and readable.
- No secrets, no unsandboxed model code, no write-capable SQL.
- Every request produces a trace and a persisted run record.

## Commands
<!-- Fill these in as the project takes shape. -->
- Install: `...`
- Run backend: `...`
- Run frontend: `...`
- Run tests: `...`
- Run evals: `...`