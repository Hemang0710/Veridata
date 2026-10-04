"""Turn a natural-language question into a single SQL statement (task 5).

Read-only safety is NOT requested here — that is the guard's job. This module
only produces a candidate SQL string via the LLM wrapper.
"""

from __future__ import annotations

import re

from opentelemetry import trace

from .llm import LLM
from .schema import SchemaSummary

tracer = trace.get_tracer("veridata")

_FENCE = re.compile(r"```(?:sql)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def _build_prompt(schema: SchemaSummary, question: str) -> str:
    return (
        "You are a SQL analyst for a DuckDB database.\n"
        "Given the schema and sample rows below, write a single SQL query that "
        "answers the question. Return only the SQL.\n\n"
        f"{schema.to_prompt()}\n\n"
        f"Question: {question}\n"
    )


def _extract_sql(text: str) -> str:
    """Pull the SQL out of a fenced block if present, else use the whole reply."""
    m = _FENCE.search(text)
    return (m.group(1) if m else text).strip()


def generate_sql(llm: LLM, schema: SchemaSummary, question: str) -> str:
    with tracer.start_as_current_span("sql_agent.generate") as span:
        prompt = _build_prompt(schema, question)
        resp = llm.generate(prompt)
        sql = _extract_sql(resp.text)
        span.set_attribute("veridata.sql", sql)
        return sql
