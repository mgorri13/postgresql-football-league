from main import (
    can_attempt_repair,
    choose_after_assessment,
    choose_after_execution,
    choose_after_validation,
)


def test_ambiguous_question_routes_to_clarification():
    state = {
        "needs_clarification": True,
    }

    assert (
        choose_after_assessment(state)
        == "ask_for_clarification"
    )


def test_clear_question_routes_to_sql_generation():
    state = {
        "needs_clarification": False,
    }

    assert choose_after_assessment(state) == "generate_sql"


def test_invalid_sql_gets_one_repair_attempt():
    state = {
        "sql_is_valid": False,
        "repair_count": 0,
    }

    assert can_attempt_repair(state) is True
    assert choose_after_validation(state) == "repair_sql"


def test_invalid_sql_stops_after_repair_limit():
    state = {
        "sql_is_valid": False,
        "repair_count": 1,
    }

    assert can_attempt_repair(state) is False

    assert (
        choose_after_validation(state)
        == "report_validation_failure"
    )


def test_execution_error_gets_one_repair_attempt():
    state = {
        "query_error": 'column "player_name" does not exist',
        "repair_count": 0,
    }

    assert choose_after_execution(state) == "repair_sql"


def test_execution_error_stops_after_repair_limit():
    state = {
        "query_error": 'column "player_name" does not exist',
        "repair_count": 1,
    }

    assert (
        choose_after_execution(state)
        == "report_query_failure"
    )


def test_successful_execution_routes_to_explanation():
    state = {
        "query_error": None,
    }

    assert choose_after_execution(state) == "explain_results"