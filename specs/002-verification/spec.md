# Spec 002 — Self-verification layer

**Status:** Ready for plan review
**Scope target:** The differentiator. Build after spec 001 is merged.

## Specify (what and why)

### Goal
Spec 001 produces an answer. This spec makes the system *trust* that answer, or
honestly say it doesn't. After each query runs, the system checks its own result,
attaches a confidence level, and abstains when confidence is low instead of
presenting a shaky number as fact. This is what separates Veridata from a plain
text-to-SQL tool, so it is built deliberately and measured.

Design choices for this slice (decided):
1. **Cheap checks first, model-as-judge second.** Run fast, deterministic checks
   that need no extra model call before spending one on an LLM judge.
2. **Show a confidence level and the reasons, and abstain when low.** The user
   sees high/medium/low, why, and a clear "I'm not sure" when the answer can't be
   trusted.
3. **Measure it.** Extend the eval seed so the verification layer's effect on
   wrong answers is a number, not a claim.

### User stories
- As a user, every answer comes with a confidence level and a short reason.
- As a user, when the system isn't confident, it tells me so plainly instead of
  giving a number that looks certain.
- As a user, I can see which checks ran and which passed or failed.

### Acceptance criteria
- Every `/ask` answer includes a `confidence` (high / medium / low) and a list of
  check results (name, passed/failed, detail).
- The deterministic checks run first and require no extra model call: the SQL
  executed without error, the result shape is sane (not unexpectedly empty, no
  all-null aggregate), and a second differently-phrased query for the same
  question returns a matching number (a consistency check).
- An LLM-as-judge check runs only after the deterministic checks and judges
  whether the SQL and result actually answer the question asked. It reuses the
  provider-agnostic wrapper and is mockable in tests.
- When checks conflict or the judge is unsure, confidence is low and the response
  abstains: it states it is not confident and why, rather than asserting the
  answer.
- The full verification outcome (every check, the confidence, the reason, the
  abstention flag) is written into the run record and emitted as spans.
- The eval harness reports, on the seed set, the wrong-answer rate with
  verification versus a no-verification baseline, so the layer's effect is
  measurable.

### Out of scope (do not build yet)
- Ambiguity detection and clarifying questions (spec 003).
- Charts and visualizations.
- Auto-correction or retrying a failed query with a new one.
- Multi-table joins and database connectors beyond the local file.

## Plan (how)

### Components
- `checks`: the deterministic checks, each a small pure function returning a
  CheckResult(name, passed, detail). No model call.
- `judge`: the LLM-as-judge check — given question, SQL, and result, returns a
  verdict and reason through the wrapper. Mockable.
- `verifier`: orchestrates checks then judge, maps the combined outcome to a
  confidence level and an abstain flag, and returns a Verification object.
- `pipeline` (extend): after `executor`, call `verifier`; fold the Verification
  into the run record and the API response. Abstention does not raise; it returns
  a low-confidence answer with the reason.
- `eval` (extend): add a baseline-vs-verified comparison over the seed set.

### Data flow
… executor -> result -> verifier (checks -> judge -> confidence + abstain)
-> response { answer, sql, confidence, checks, trace_id } + run record.

### Key decisions
- Deterministic checks gate the expensive judge: if they already prove the answer
  untrustworthy, confidence is low without spending a model call.
- The consistency check generates one alternate SQL for the same question and
  compares the headline number; a mismatch is a strong low-confidence signal.
- Confidence mapping lives in one place in `verifier`, so the rules are legible
  and testable, not scattered.
- The judge is advisory, never a safety gate; the guard from spec 001 remains the
  only thing that authorizes execution.

## Tasks
1. `checks`: SQL-executed, result-shape, and consistency checks as pure
   functions, each returning a CheckResult. Unit tests per check, including the
   failing cases.
2. `judge`: LLM-as-judge verdict through the wrapper, with a mock for tests.
3. `verifier`: run checks then judge, map to confidence + abstain, return a
   Verification. Unit tests covering high, medium, low, and abstain paths.
4. Extend `pipeline` and the run record to carry the Verification, with a span
   per check and for the judge.
5. Extend `/ask` response to include `confidence` and `checks`; update the API
   tests.
6. Extend the eval harness to report wrong-answer rate verified vs. baseline on
   the seed set.
