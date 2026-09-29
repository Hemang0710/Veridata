# Product Requirements Document — Veridata (working title)

> A data analyst agent that verifies its own answers.

**Owner:** Hemang Patel
**Status:** Draft v0.1
**Last updated:** 2026-09-26

## 1. Problem
People ask questions of their data in plain English and get back a confident
number and a chart. On realistic, messy data, today's text-to-SQL tools are
wrong roughly one time in five, and they give the user no signal about which
time. The unsolved problem is not generating SQL. It is trusting the answer.

## 2. Target user
A data-literate but non-expert user (analyst, PM, founder, operator) who can
read a chart and a number but cannot easily audit whether a generated query is
correct. Secondary user: the technical reviewer evaluating this project, who
cares about correctness and engineering rigor.

## 3. What makes this different (the wedge)
Every competitor generates an answer. This product generates an answer **and
proves it**:
- Self-verification of each result before it is shown.
- Detection of ambiguous questions, with a clarifying question instead of a
  silent guess.
- A confidence level and the ability to abstain ("I'm not sure") rather than
  fabricate.
- Every answer ships with its SQL/Python, assumptions, and row counts, fully
  auditable.

## 4. Goals and success metrics
- **Primary:** Execution accuracy on a fixed BIRD/Spider subset at or above a
  stated baseline, AND a measurable reduction in "confidently wrong" answers
  (wrong answers returned at high confidence) versus a naive single-shot
  baseline.
- **Secondary:** Median time-to-answer within an acceptable bound; every answer
  includes a reproducible artifact.

## 5. Non-goals (out of scope for v1)
- Not a BI / dashboarding product (no saved dashboards, scheduling, alerts).
- Not multi-user, no enterprise governance, no role-based access.
- Not real-time or streaming data.
- Not a general observability platform.
- No fine-tuned models; use frontier models via API.

## 6. Core features (v1)
1. Upload a CSV (and/or connect a SQLite/DuckDB database).
2. Ask a question in natural language.
3. Receive: the answer, the SQL/Python used, assumptions made, row counts, and
   a confidence level.
4. If the question is ambiguous, receive a clarifying question first.
5. A basic chart when the result is chartable.
6. An eval harness that scores the agent against a benchmark subset.

## 7. Constraints
- Solo developer, Industry standard product (correctness and rigor over
  feature breadth).
- Built with a spec-driven, AI-assisted workflow.
