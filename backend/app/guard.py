"""Read-only SQL guard: the safety boundary (task 6).

Rejects anything that is not a single read-only SELECT, enforced in code — the
model is never trusted for safety. Fails closed: an ambiguous parse is rejected.
"""

from __future__ import annotations

from opentelemetry import trace

tracer = trace.get_tracer("veridata")


class GuardRejection(ValueError):
    """Raised when SQL is not a single read-only SELECT."""


def _scan(sql: str) -> list[str]:
    """Split into statements, stripping comments while respecting string literals.

    Single-quoted literals (with '' escaping) are preserved verbatim, so a `;`,
    `--`, or `/* */` inside a string does not end a statement or start a comment.
    """
    statements: list[str] = []
    current: list[str] = []
    i, n = 0, len(sql)
    while i < n:
        c = sql[i]
        if c == "'":  # string literal — copy through, handle '' escape
            current.append(c)
            i += 1
            while i < n:
                current.append(sql[i])
                if sql[i] == "'":
                    if i + 1 < n and sql[i + 1] == "'":
                        current.append(sql[i + 1])
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
            continue
        if c == "-" and i + 1 < n and sql[i + 1] == "-":  # line comment
            i += 2
            while i < n and sql[i] != "\n":
                i += 1
            continue
        if c == "/" and i + 1 < n and sql[i + 1] == "*":  # block comment
            i += 2
            while i + 1 < n and not (sql[i] == "*" and sql[i + 1] == "/"):
                i += 1
            i += 2
            continue
        if c == ";":
            statements.append("".join(current))
            current = []
            i += 1
            continue
        current.append(c)
        i += 1
    statements.append("".join(current))
    return [s.strip() for s in statements if s.strip()]


def guard_sql(sql: str) -> str:
    """Return the validated single SELECT statement, or raise GuardRejection."""
    with tracer.start_as_current_span("guard.check") as span:

        def reject(reason: str) -> None:
            span.set_attribute("veridata.guard.decision", "reject")
            span.set_attribute("veridata.guard.reason", reason)
            raise GuardRejection(reason)

        statements = _scan(sql)
        if not statements:
            reject("empty statement")
        if len(statements) > 1:
            reject("multiple statements")

        stmt = statements[0]
        head = stmt.lstrip("( \t\r\n").split(None, 1)[0].upper() if stmt else ""
        if head not in {"SELECT", "WITH"}:
            reject(f"non-SELECT statement: {head or '(none)'}")

        span.set_attribute("veridata.guard.decision", "allow")
        return stmt
