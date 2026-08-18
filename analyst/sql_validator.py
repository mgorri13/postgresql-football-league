import sqlglot
from pydantic import BaseModel
from sqlglot import exp
from sqlglot.errors import ParseError


ALLOWED_TABLES = {
    "seasons",
    "teams",
    "players",
    "matches",
    "goals",
    "lineups",
    "cards",
    "substitutions",
    "player_match_stats",
    "player_rolling_form",
    "season_standings",
}


class SqlValidationResult(BaseModel):
    is_valid: bool
    errors: list[str]
    referenced_tables: list[str]


def validate_sql(sql: str) -> SqlValidationResult:
    if not sql.strip():
        return SqlValidationResult(
            is_valid=False,
            errors=["SQL cannot be empty."],
            referenced_tables=[],
        )

    try:
        statements = [
            statement
            for statement in sqlglot.parse(sql, read="postgres")
            if statement is not None
        ]
    except ParseError as error:
        return SqlValidationResult(
            is_valid=False,
            errors=[f"SQL syntax error: {error}"],
            referenced_tables=[],
        )

    if len(statements) != 1:
        return SqlValidationResult(
            is_valid=False,
            errors=["Exactly one SQL statement is allowed."],
            referenced_tables=[],
        )

    statement = statements[0]
    errors = []

    if (
        not isinstance(statement, exp.Query)
        or statement.find(exp.Select) is None
    ):
        errors.append("Only SELECT queries are allowed.")

    if statement.find(exp.Into) is not None:
        errors.append("SELECT INTO is not allowed.")

    cte_names = {
        cte.alias_or_name.lower()
        for cte in statement.find_all(exp.CTE)
        if cte.alias_or_name
    }

    referenced_tables = {
        table.name.lower()
        for table in statement.find_all(exp.Table)
        if table.name
    }

    unknown_tables = referenced_tables - ALLOWED_TABLES - cte_names

    if unknown_tables:
        errors.append(
            "Query references tables that are not allowed: "
            + ", ".join(sorted(unknown_tables))
        )

    return SqlValidationResult(
        is_valid=not errors,
        errors=errors,
        referenced_tables=sorted(referenced_tables),
    )


if __name__ == "__main__":
    examples = {
        "valid query": """
            SELECT
                players.first_name,
                players.last_name,
                COUNT(goals.id) AS goals_scored
            FROM goals
            JOIN players ON players.id = goals.scorer_id
            GROUP BY players.id, players.first_name, players.last_name
            ORDER BY goals_scored DESC
            LIMIT 5;
        """,
        "syntax error": """
            SELECT * FROM players ORDER BYgoals_scored DESC;
        """,
        "multiple statements": """
            SELECT * FROM players;
            DROP TABLE players;
        """,
        "write query": """
            DELETE FROM players;
        """,
        "unknown table": """
            SELECT * FROM secret_payroll;
        """,
    }

    for name, sql in examples.items():
        print(f"\n{name}:")
        print(validate_sql(sql).model_dump())