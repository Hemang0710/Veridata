import pytest

from app.guard import GuardRejection, guard_sql

ALLOWED = [
    "SELECT * FROM data",
    "select 1",
    "WITH t AS (SELECT 1 AS n) SELECT * FROM t",
    "SELECT 1;",  # single trailing semicolon
    "-- fetch everything\nSELECT * FROM data",  # leading line comment
    "/* note */ SELECT * FROM data",  # leading block comment
    "SELECT '; DROP TABLE data' AS s",  # semicolon inside a string literal
    "SELECT '-- not a comment' AS s",  # comment marker inside a string literal
]

REJECTED = [
    "INSERT INTO data VALUES (1)",
    "UPDATE data SET id = 1",
    "DELETE FROM data",
    "DROP TABLE data",
    "ALTER TABLE data ADD COLUMN x INT",
    "CREATE TABLE t (x INT)",
    "COPY data TO 'out.csv'",
    "SELECT 1; DROP TABLE data",  # write after a valid select
    "SELECT 1; SELECT 2",  # multiple statements
    "SELECT 1; -- ok\nDROP TABLE data",  # write hidden after a comment
    "/* SELECT 1 */ DROP TABLE data",  # select hidden in a comment
    "-- SELECT 1\nDROP TABLE data",
    "",
    "   ",
]


@pytest.mark.parametrize("sql", ALLOWED)
def test_guard_allows_read_only_selects(sql):
    assert guard_sql(sql)  # returns a non-empty statement


@pytest.mark.parametrize("sql", REJECTED)
def test_guard_rejects_non_selects_and_multi_statements(sql):
    with pytest.raises(GuardRejection):
        guard_sql(sql)
