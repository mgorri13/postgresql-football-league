import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

from sql_validator import validate_sql


load_dotenv(Path(__file__).with_name(".env"))
MAX_RESULT_ROWS = 100


def get_connection():
    return psycopg.connect(
        host=os.environ["FOOTBALL_DB_HOST"],
        port=os.environ["FOOTBALL_DB_PORT"],
        dbname=os.environ["FOOTBALL_DB_NAME"],
        user=os.environ["FOOTBALL_DB_USER"],
        password=os.environ["FOOTBALL_DB_PASSWORD"],
        row_factory=dict_row,
        options="-c default_transaction_read_only=on -c statement_timeout=5000",
    )

def execute_approved_query(sql: str):
    validation = validate_sql(sql)

    if not validation.is_valid:
        raise ValueError(
            "Refusing to execute invalid SQL: "
            + "; ".join(validation.errors)
        )

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql)

            if cursor.description is None:
                raise ValueError("The query did not return rows.")

            return cursor.fetchmany(MAX_RESULT_ROWS)

def get_top_scorers(limit: int = 5):
    query = """
        SELECT
            players.first_name,
            players.last_name,
            teams.name AS team_name,
            COUNT(goals.id) AS goals_scored
        FROM goals
        JOIN players ON players.id = goals.scorer_id
        JOIN teams ON teams.id = players.team_id
        GROUP BY
            players.id,
            players.first_name,
            players.last_name,
            teams.name
        ORDER BY goals_scored DESC, players.last_name
        LIMIT %s;
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, (limit,))
            return cursor.fetchall()


def check_database_access():
    query = """
        SELECT
            current_user,
            current_setting('transaction_read_only') AS transaction_read_only,
            has_table_privilege(
                current_user,
                'public.matches',
                'SELECT'
            ) AS can_select,
            has_table_privilege(
                current_user,
                'public.matches',
                'INSERT'
            ) AS can_insert;
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchone()


if __name__ == "__main__":
    print("Database access check:")
    print(check_database_access())

    print("\nTop scorers:")
    for scorer in get_top_scorers():
        print(scorer)