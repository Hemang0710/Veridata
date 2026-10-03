from app.llm import MockLLM
from app.schema import SchemaSummary
from app.ingest import Column
from app.sql_agent import generate_sql

SCHEMA = SchemaSummary(
    table="data",
    columns=[Column("id", "BIGINT"), Column("name", "VARCHAR")],
    sample_rows=[{"id": 1, "name": "Alice"}],
)


def test_generate_sql_strips_fences_and_builds_prompt():
    llm = MockLLM("```sql\nSELECT count(*) FROM data\n```")
    sql = generate_sql(llm, SCHEMA, "How many rows are there?")

    assert sql == "SELECT count(*) FROM data"
    assert "How many rows are there?" in llm.last_prompt
    assert "name" in llm.last_prompt  # schema summary reached the model


def test_generate_sql_accepts_unfenced_reply():
    llm = MockLLM("SELECT name FROM data")
    assert generate_sql(llm, SCHEMA, "names?") == "SELECT name FROM data"
