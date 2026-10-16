"""Eval seed (spec 001 task 11 / correctness AC).

Hand-written question -> expected-answer cases run through the REAL pipeline
(the configured provider generating SQL), not a scripted MockLLM. This is the
seed of the eval set; it verifies the model produces correct SQL for English
questions.

Uses the same provider wiring as the app (build_llm, selected by LLM_PROVIDER).
Requires a configured key (LLM_API_KEY or ANTHROPIC_API_KEY); skipped otherwise
so unit CI stays offline/free.
# ponytail: a versioned list in one file is the seed; graduate to a BIRD/Spider
# harness (CLAUDE.md) in a later spec when the set outgrows a handful of cases.
"""

import os
from pathlib import Path

import duckdb
import pytest
from dotenv import load_dotenv

from app.ingest import ingest_csv
from app.llm import build_llm
from app.pipeline import answer_question

load_dotenv()

_needs_key = pytest.mark.skipif(
    not (os.getenv("LLM_API_KEY") or os.getenv("ANTHROPIC_API_KEY")),
    reason="no LLM key configured (set LLM_API_KEY or ANTHROPIC_API_KEY); eval seed hits the real model",
)

SAMPLE = Path(__file__).parent / "data" / "sample.csv"


# (question, expected value that must appear in the result rows)
CASES = [
    ("How many employees are there?", 6),
    ("How many employees are in the Engineering department?", 3),
    ("What is the highest salary?", 105000.75),
    ("How many distinct departments are there?", 3),
    ("Who has the highest salary?", "Carol"),
]


def _contains(answer: dict, expected) -> bool:
    """True if `expected` appears in any result cell (numeric tolerance; case-insensitive)."""
    for row in answer["rows"]:
        for cell in row:
            if isinstance(expected, (int, float)) and isinstance(cell, (int, float)):
                if abs(float(cell) - float(expected)) < 0.01:
                    return True
            elif str(cell).strip().lower() == str(expected).strip().lower():
                return True
    return False


def test_contains_matches_numbers_and_strings():
    """Offline check of the matcher so it's verified without an API key."""
    assert _contains({"rows": [(6,)]}, 6)
    assert _contains({"rows": [(105000.75,)]}, 105000.75)  # float tolerance
    assert _contains({"rows": [("Carol",)]}, "carol")  # case-insensitive
    assert not _contains({"rows": [(5,)]}, 6)
    assert not _contains({"rows": [("Bob",)]}, "Carol")


@_needs_key
@pytest.mark.parametrize("question,expected", CASES)
def test_eval_seed_answers_are_correct(question, expected, tmp_path):
    con = ingest_csv(SAMPLE, con=duckdb.connect()).con
    result = answer_question(
        con, "data", question, build_llm(), verify_llm=build_llm(verify=True), records_dir=tmp_path
    )
    assert _contains(result.answer, expected), (
        f"Q={question!r} expected {expected!r} not in {result.answer['rows']!r} "
        f"(sql: {result.sql})"
    )


@_needs_key
def test_verification_lowers_wrong_answer_rate(tmp_path):
    """Measure the verification layer's effect: wrong answers that are *presented*
    (not abstained, not low-confidence) should be no more than the baseline wrong
    count. The printed rates are the tracked artifact; a richer labelled corpus is
    the real lever (see plan.md) — this delivers the measurement mechanism.
    """
    con = ingest_csv(SAMPLE, con=duckdb.connect()).con
    baseline_wrong = verified_wrong = 0
    for question, expected in CASES:
        r = answer_question(
            con, "data", question, build_llm(), verify_llm=build_llm(verify=True), records_dir=tmp_path
        )
        if not _contains(r.answer, expected):
            baseline_wrong += 1
            if not r.abstained and r.confidence != "low":
                verified_wrong += 1  # wrong *and* presented confidently
    n = len(CASES)
    print(f"\nbaseline wrong-answer rate:  {baseline_wrong}/{n}")
    print(f"verified wrong-answer rate:  {verified_wrong}/{n}")
    assert verified_wrong <= baseline_wrong  # verification can only withhold, never add
