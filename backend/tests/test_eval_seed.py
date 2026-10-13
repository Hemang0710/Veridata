"""Eval seed (spec 001 task 11 / correctness AC).

Hand-written question -> expected-answer cases run through the REAL pipeline
(AnthropicLLM generating SQL), not a scripted MockLLM. This is the seed of the
eval set; it verifies the model produces correct SQL for English questions.

Requires ANTHROPIC_API_KEY; skipped otherwise so unit CI stays offline/free.
# ponytail: a versioned list in one file is the seed; graduate to a BIRD/Spider
# harness (CLAUDE.md) in a later spec when the set outgrows a handful of cases.
"""

import os

import duckdb
import pytest
from dotenv import load_dotenv

from app.ingest import ingest_csv
from app.llm import AnthropicLLM
from app.pipeline import answer_question

load_dotenv()

_needs_key = pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set; eval seed hits the real model",
)

SAMPLE = "tests/data/sample.csv"

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
    result = answer_question(con, "data", question, AnthropicLLM(), records_dir=tmp_path)
    assert _contains(result.answer, expected), (
        f"Q={question!r} expected {expected!r} not in {result.answer['rows']!r} "
        f"(sql: {result.sql})"
    )
