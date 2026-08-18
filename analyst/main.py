import argparse
from pprint import pprint
from typing import NotRequired, TypedDict

import psycopg
from langgraph.graph import END, START, StateGraph

from database import execute_approved_query
from result_explainer import explain_query_results
from sql_generator import generate_sql_proposal, repair_sql_proposal
from sql_validator import validate_sql
from question_router import assess_question

MAX_REPAIR_ATTEMPTS = 1

class AnalystState(TypedDict):
    question: str
    normalised_question: NotRequired[str]
    answer: NotRequired[str]
    interpretation: NotRequired[str]
    proposed_sql: NotRequired[str]
    sql_is_valid: NotRequired[bool]
    validation_errors: NotRequired[list[str]]
    referenced_tables: NotRequired[list[str]]
    approved_sql: NotRequired[str]
    query_rows: NotRequired[list[dict]]
    query_error: NotRequired[str | None]
    repair_count: NotRequired[int]
    needs_clarification: NotRequired[bool]
    clarification_question: NotRequired[str | None]

def normalise_question(state: AnalystState) -> dict:
    clean_question = " ".join(state["question"].strip().split())

    return {
        "normalised_question": clean_question,
    }

def assess_user_question(state: AnalystState) -> dict:
    assessment = assess_question(
        state["normalised_question"]
    )

    return {
        "needs_clarification": assessment.needs_clarification,
        "clarification_question": assessment.clarification_question,
    }

def generate_sql(state: AnalystState) -> dict:
    proposal = generate_sql_proposal(
        state["normalised_question"]
    )

    return {
        "interpretation": proposal.interpretation,
        "proposed_sql": proposal.sql,
    }



def validate_generated_sql(state: AnalystState) -> dict:
    result = validate_sql(state["proposed_sql"])

    updates = {
        "sql_is_valid": result.is_valid,
        "validation_errors": result.errors,
        "referenced_tables": result.referenced_tables,
    }

    if result.is_valid:
        updates["approved_sql"] = state["proposed_sql"]

    return updates


def execute_approved_sql(state: AnalystState) -> dict:
    try:
        rows = execute_approved_query(state["approved_sql"])
    except psycopg.Error as error:
        return {
            "query_rows": [],
            "query_error": str(error),
        }

    return {
        "query_rows": rows,
        "query_error": None,
    }

def can_attempt_repair(state: AnalystState) -> bool:
    return state.get("repair_count", 0) < MAX_REPAIR_ATTEMPTS


def repair_sql(state: AnalystState) -> dict:
    if state.get("query_error"):
        error_feedback = state["query_error"]
    else:
        error_feedback = "; ".join(state["validation_errors"])

    proposal = repair_sql_proposal(
        question=state["normalised_question"],
        intended_interpretation=state["interpretation"],
        failed_sql=state["proposed_sql"],
        error_feedback=error_feedback,
    )

    return {
        "interpretation": proposal.interpretation,
        "proposed_sql": proposal.sql,
        "repair_count": state.get("repair_count", 0) + 1,
        "query_error": None,
    }

def explain_results(state: AnalystState) -> dict:
    explanation = explain_query_results(
        question=state["normalised_question"],
        interpretation=state["interpretation"],
        rows=state["query_rows"],
    )

    return {
        "answer": explanation.answer,
    }


def report_validation_failure(state: AnalystState) -> dict:
    errors = "; ".join(state["validation_errors"])

    return {
        "answer": (
            "I could not prepare a safe SQL query for this question. "
            f"Reason: {errors}"
        )
    }


def report_query_failure(state: AnalystState) -> dict:
    return {
        "answer": (
            "I prepared a safe query, but the database could not execute it. "
            f"Database message: {state['query_error']}"
        )
    }


def ask_for_clarification(state: AnalystState) -> dict:
    question = state["clarification_question"]

    if question is None:
        question = "Please clarify what you would like to know."

    return {
        "answer": question,
    }


def choose_after_assessment(state: AnalystState) -> str:
    if state["needs_clarification"]:
        return "ask_for_clarification"

    return "generate_sql"


def choose_after_validation(state: AnalystState) -> str:
    if state["sql_is_valid"]:
        return "execute_approved_sql"

    if can_attempt_repair(state):
        return "repair_sql"

    return "report_validation_failure"


def choose_after_execution(state: AnalystState) -> str:
    if state.get("query_error"):
        if can_attempt_repair(state):
            return "repair_sql"

        return "report_query_failure"

    return "explain_results"


builder = StateGraph(AnalystState)

builder.add_node("normalise_question", normalise_question)
builder.add_node("generate_sql", generate_sql)
builder.add_node("validate_generated_sql", validate_generated_sql)
builder.add_node("execute_approved_sql", execute_approved_sql)
builder.add_node("explain_results", explain_results)
builder.add_node("report_validation_failure", report_validation_failure)
builder.add_node("report_query_failure", report_query_failure)
builder.add_node("ask_for_clarification", ask_for_clarification)
builder.add_node("repair_sql", repair_sql)
builder.add_node("assess_user_question", assess_user_question)

builder.add_edge(START, "normalise_question")

builder.add_edge("normalise_question", "assess_user_question")

builder.add_conditional_edges(
    "assess_user_question",
    choose_after_assessment,
    {
        "generate_sql": "generate_sql",
        "ask_for_clarification": "ask_for_clarification",
    },
)

builder.add_edge("generate_sql", "validate_generated_sql")

builder.add_conditional_edges(
    "validate_generated_sql",
    choose_after_validation,
    {
        "execute_approved_sql": "execute_approved_sql",
        "repair_sql": "repair_sql",
        "report_validation_failure": "report_validation_failure",
    },
)

builder.add_conditional_edges(
    "execute_approved_sql",
    choose_after_execution,
    {
        "explain_results": "explain_results",
        "repair_sql": "repair_sql",
        "report_query_failure": "report_query_failure",
    },
)

builder.add_edge("explain_results", END)
builder.add_edge("report_validation_failure", END)
builder.add_edge("report_query_failure", END)
builder.add_edge("ask_for_clarification", END)
builder.add_edge("repair_sql", "validate_generated_sql")

graph = builder.compile()

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Ask questions about the football database."
    )

    parser.add_argument(
        "question",
        nargs="*",
        help="Your football question.",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show the LangGraph state after every node.",
    )

    return parser.parse_args()


def run_question(question: str, debug: bool) -> dict:
    input_state = {
        "question": question,
    }

    if not debug:
        return graph.invoke(input_state)

    final_state = {}

    for event in graph.stream(
        input_state,
        stream_mode="values",
        version="v2",
    ):
        if event["type"] == "values":
            final_state = event["data"]
            pprint(final_state)

    return final_state

def run_conversation(question: str, debug: bool) -> dict:
    current_question = question

    while True:
        final_state = run_question(
            question=current_question,
            debug=debug,
        )

        print("\nAnswer:")
        print(final_state["answer"])

        if not final_state.get("needs_clarification"):
            return final_state

        clarification = input(
            "\nYour clarification: "
        ).strip()

        if not clarification:
            print("No clarification was provided.")
            return final_state

        current_question = (
            f"Original question: {current_question}\n"
            f"User clarification: {clarification}"
        )

def main():
    args = parse_arguments()

    question = " ".join(args.question).strip()

    if not question:
        question = input("Ask a football question: ").strip()

    if not question:
        print("No question was provided.")
        return

    try:
        run_conversation(
            question=question,
            debug=args.debug,
        )
    except KeyboardInterrupt:
        print("\nCancelled.")
        return
    except Exception as error:
        print("The analyst could not complete this request.")

        if args.debug:
            raise error

        return

    


if __name__ == "__main__":
    main()