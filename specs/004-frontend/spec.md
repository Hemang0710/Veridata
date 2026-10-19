# Spec 004 — Verified chat frontend

**Status:** Ready for plan review
**Scope target:** Make the product visible and demoable. Build after the
verification fix is merged.

## Specify (what and why)

### Goal
Everything so far lives in the `/docs` API tester. This spec gives Veridata a
real web interface: upload a CSV, ask a question in plain English, and get the
answer back with its **trust signals shown first** — the confidence level and,
when the system abstains, the reason. The SQL and the individual checks are
available in a "show your work" panel. This is the piece that turns a working
backend into something a person (or a recruiter) can use and screenshot.

Decisions (made):
1. **Verification is front and center.** The confidence badge and abstain reason
   are the most prominent part of each answer, not hidden.
2. **Charts are out of scope here** — they are a separate spec (005) built on top
   of this once the verified chat UI is solid.

### User stories
- As a user, I can upload a CSV and see it loaded (columns, row count).
- As a user, I can type a question and get an answer.
- As a user, the first thing I see about an answer is how much to trust it: a
  clear confidence badge (high / medium / low) and, if it abstained, why.
- As a user, I can expand a "show your work" panel to see the exact SQL, the
  result, and each check with its pass/fail and detail.
- As a user, I can see the trace ID for an answer so a problem is traceable.

### Acceptance criteria
- A user can upload a CSV through the UI; on success the UI shows the detected
  columns and the row count.
- A user can submit a question and receive the answer rendered in the UI.
- Each answer displays a prominent confidence indicator, colour-coded:
  high = green, medium = amber, low/abstained = red, with the abstain reason
  shown in plain text when present.
- A collapsible "show your work" panel shows the SQL, the returned rows, and the
  list of checks (name, passed/failed, detail).
- Guard rejections and errors are shown as a clear message, not a crash.
- The UI talks to the existing `/upload` and `/ask` endpoints; no backend changes
  beyond CORS if needed.
- The app runs locally against the local backend, and builds cleanly for deploy.

### Out of scope (do not build here)
- Charts and visualizations (spec 005).
- Auth, accounts, saved history, multi-user.
- Multiple simultaneous datasets.
- Editing or re-running past answers.
- Server-side rendering of data; this is a thin client over the API.

## Plan (how)

### Components
- `UploadPanel`: file picker → `POST /upload` → shows columns + row count.
- `QuestionBox`: text input → `POST /ask` → loading state → result.
- `AnswerCard`: renders the answer value, and **prominently** the confidence
  badge + abstain reason. Contains the collapsible `ShowYourWork`.
- `ConfidenceBadge`: maps high/medium/low(+abstained) to colour and label.
- `ShowYourWork`: collapsible panel with SQL (monospaced), result rows (simple
  table), and the checks list.
- `api` client: small typed wrapper for `/upload` and `/ask`, base URL from env.

### Data flow
CSV → UploadPanel → `/upload` → columns/row_count shown.
Question → QuestionBox → `/ask` → { answer, sql, confidence, abstained, reason,
checks, trace_id } → AnswerCard (badge first, work on demand).

### Key decisions
- Next.js (App Router) + React, deployed on Vercel per the constitution.
- Thin client: no business logic in the frontend; it renders what the API
  returns. Confidence and checks come from the backend, never recomputed here.
- Backend base URL from an env var (e.g. `NEXT_PUBLIC_API_BASE_URL`) so local and
  deployed point at the right place.
- Keep styling simple and clean; the trust signals are the visual priority.

## Tasks
1. Scaffold the Next.js app under `frontend/` (App Router, TypeScript), with the
   API base URL read from env and a README note on running it.
2. `api` client: typed `upload()` and `ask()` functions against the two
   endpoints, with error handling.
3. `UploadPanel`: upload a CSV, show columns + row count, handle errors.
4. `QuestionBox` + `AnswerCard`: submit a question, render the answer with the
   `ConfidenceBadge` prominent and the abstain reason when present.
5. `ShowYourWork`: collapsible SQL + result table + checks list.
6. Wire CORS on the backend if the browser blocks cross-origin calls (smallest
   change needed).
7. Manual check: run the backend, run the frontend, upload `employees_test.csv`,
   ask "how many employees" (expect green/high) and "what is the average age"
   (expect red/abstain with reason). Confirm the badge and reason are the
   prominent elements.
