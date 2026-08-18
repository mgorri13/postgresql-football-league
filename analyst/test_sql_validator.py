from analyst.sql_validator import validate_sql


def test_accepts_safe_select_query():
    result = validate_sql(
        "SELECT first_name, last_name FROM players LIMIT 5;"
    )

    assert result.is_valid is True
    assert result.errors == []
    assert result.referenced_tables == ["players"]


def test_rejects_multiple_statements():
    result = validate_sql(
        "SELECT * FROM players; DROP TABLE players;"
    )

    assert result.is_valid is False
    assert "Exactly one SQL statement is allowed." in result.errors


def test_rejects_write_query():
    result = validate_sql(
        "DELETE FROM players;"
    )

    assert result.is_valid is False
    assert "Only SELECT queries are allowed." in result.errors


def test_rejects_unknown_table():
    result = validate_sql(
        "SELECT * FROM secret_payroll;"
    )

    assert result.is_valid is False
    assert (
        "Query references tables that are not allowed: secret_payroll"
        in result.errors
    )


def test_rejects_invalid_syntax():
    result = validate_sql(
        "SELECT * FROM players ORDER BYgoals_scored DESC;"
    )

    assert result.is_valid is False
    assert "SQL syntax error:" in result.errors[0]