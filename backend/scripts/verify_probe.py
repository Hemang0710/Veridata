"""Exercise the verification layer end to end against the live configured provider.

Loads employees_test.csv into DuckDB and runs answer_question over a handful of
probes chosen to hit each confidence outcome (high / medium / low+abstain), then
writes a reviewable report to backend/verify_probe_results.md.

This is a manual probe, not a test: it calls the real LLM provider, so it needs
the same env the app uses (.env with ANTHROPIC_API_KEY, or LLM_PROVIDER + keys).
Run it from anywhere: `python backend/scripts/verify_probe.py`.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # before building the LLM, mirroring app.main

# Make `app` importable whether run from repo root or the scripts dir.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ingest import ingest_csv  # noqa: E402
from app.llm import build_llm  # noqa: E402
from app.pipeline import PipelineRejected, answer_question  # noqa: E402

CSV = Path(__file__).resolve().parent / "employees_test.csv"
OUT = Path(__file__).resolve().parents[1] / "verify_probe_results.md"

# (question, expected label, predicate on confidence/abstained). Predicate None =
# "watch only", no pass/fail — just report what happened.
PROBES: list[tuple[str, str, object]] = [
    ("How many employees are there?", "high", lambda c, a: c == "high"),
    ("What is the average age of employees?", "low / abstain", lambda c, a: c == "low" or a),
    ("Who are the top employees?", "medium or low", lambda c, a: c in {"medium", "low"}),
    ("Who has the highest salary?", "medium or high", lambda c, a: c in {"medium", "high"}),
    ("What is the average salary?", "watch (one salary is blank)", None),
]


def _cell(text: object) -> str:
    """Make a value safe for one markdown table cell: no raw pipes or newlines."""
    return str(text).replace("|", "\\|").replace("\n", " ").strip()


def _fmt_answer(answer: dict) -> str:
    cols = answer.get("columns", [])
    rows = answer.get("rows", [])
    shown = "; ".join(str(tuple(r)) for r in rows[:5])
    more = f" (+{len(rows) - 5} more rows)" if len(rows) > 5 else ""
    return f"columns={cols} rows={shown or '(none)'}{more}"


def _checks_summary(checks: list[dict]) -> str:
    return " ".join(f"{c['name']}:{'OK' if c['passed'] else 'X'}" for c in checks) or "(none ran)"


def main() -> int:
    if not CSV.exists():
        print(f"missing fixture: {CSV}", file=sys.stderr)
        return 1

    provider = os.getenv("LLM_PROVIDER", "anthropic")
    llm = build_llm()
    verify_llm = build_llm(verify=True)
    ds = ingest_csv(CSV)
    print(f"Loaded {ds.row_count} rows, columns: {[c.name for c in ds.columns]}")

    records = []
    for question, expected, predicate in PROBES:
        print(f"-> {question}")
        try:
            r = answer_question(ds.con, ds.table, question, llm, verify_llm=verify_llm)
            rec = {
                "question": question,
                "expected": expected,
                "sql": r.sql,
                "answer": _fmt_answer(r.answer),
                "confidence": r.confidence,
                "abstained": r.abstained,
                "reason": r.reason,
                "checks": r.checks,
            }
        except PipelineRejected as exc:
            # The guard rejected the SQL before execution — a real outcome worth seeing.
            rec = {
                "question": question,
                "expected": expected,
                "sql": exc.sql,
                "answer": "(guard rejected — no execution)",
                "confidence": "rejected",
                "abstained": True,
                "reason": f"guard rejected: {exc.reason}",
                "checks": [],
            }
        except Exception as exc:  # noqa: BLE001 — a probe failing must not sink the report
            rec = {
                "question": question,
                "expected": expected,
                "sql": "(error before/at execution)",
                "answer": f"ERROR: {exc}",
                "confidence": "error",
                "abstained": True,
                "reason": str(exc),
                "checks": [],
            }
        if predicate is None:
            rec["match"] = None  # watch-only
        else:
            rec["match"] = bool(predicate(rec["confidence"], rec["abstained"]))
        records.append(rec)

    _write_report(records, provider, getattr(llm, "model", "?"), getattr(verify_llm, "model", "?"))
    print(f"\nWrote {OUT}")
    return 0


def _write_report(records: list[dict], provider: str, model: str, verify_model: str) -> None:
    lines: list[str] = []
    lines.append("# Verification probe results")
    lines.append("")
    lines.append(
        f"_Generated {datetime.now().isoformat(timespec='seconds')} against provider "
        f"`{provider}` (answer model `{model}`, verify model `{verify_model}`)._"
    )
    lines.append("")

    # Summary table (the 6 requested columns).
    lines.append("## Summary")
    lines.append("")
    lines.append("| Question | Expected | Confidence | Abstained | Reason | Checks summary |")
    lines.append("|---|---|---|---|---|---|")
    for r in records:
        lines.append(
            f"| {_cell(r['question'])} | {_cell(r['expected'])} | {_cell(r['confidence'])} "
            f"| {_cell(r['abstained'])} | {_cell(r['reason'])} | {_cell(_checks_summary(r['checks']))} |"
        )
    lines.append("")

    # Full per-probe detail: SQL, answer, and every check with pass/fail + detail.
    lines.append("## Details")
    lines.append("")
    for i, r in enumerate(records, 1):
        verdict = {True: "MATCH", False: "MISMATCH", None: "watch only"}[r["match"]]
        lines.append(f"### {i}. {r['question']}")
        lines.append("")
        lines.append(f"- Expected: {r['expected']}  —  **{verdict}**")
        lines.append(f"- Confidence: `{r['confidence']}`  |  Abstained: `{r['abstained']}`")
        lines.append(f"- Reason: {r['reason']}")
        lines.append(f"- Answer: {r['answer']}")
        lines.append("- SQL:")
        lines.append("")
        lines.append("```sql")
        lines.append(r["sql"])
        lines.append("```")
        lines.append("- Checks:")
        if r["checks"]:
            for c in r["checks"]:
                mark = "OK" if c["passed"] else "X"
                lines.append(f"  - `{c['name']}` — {mark} — {c['detail']}")
        else:
            lines.append("  - (none ran)")
        lines.append("")

    scored = [r for r in records if r["match"] is not None]
    matched = [r for r in scored if r["match"]]
    names = ", ".join(
        f"{r['question']} ({'match' if r['match'] else 'MISMATCH'})" for r in scored
    )
    lines.append(
        f"**{len(matched)}/{len(scored)} probes matched their expectation.** {names}"
    )
    lines.append("")
    OUT.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
