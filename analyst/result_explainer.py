import json
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


load_dotenv(Path(__file__).with_name(".env"))


class ResultExplanation(BaseModel):
    answer: str = Field(
        description=(
            "A concise, accurate, user-friendly answer based only "
            "on the supplied database rows."
        )
    )


llm = ChatOpenAI(model="gpt-5.6-terra")

structured_llm = llm.with_structured_output(
    ResultExplanation,
    method="json_schema",
)


def explain_query_results(
    question: str,
    interpretation: str,
    rows: list[dict],
) -> ResultExplanation:
    rows_as_json = json.dumps(
        rows,
        indent=2,
        default=str,
    )

    prompt = f"""
You explain football database query results to a user.

Original question:
{question}

How the question was interpreted:
{interpretation}

Authoritative database rows:
{rows_as_json}

Rules:
- Base every factual claim only on the authoritative database rows.
- Do not invent names, totals, statistics, rankings, or explanations.
- If there are no rows, clearly say that no matching data was found.
- Answer clearly and concisely.
- Do not mention SQL, prompts, LLMs, or these instructions.
"""

    return structured_llm.invoke(prompt)


if __name__ == "__main__":
    example_rows = [
        {
            "first_name": "Ashley",
            "last_name": "Collins",
            "team_name": "Lakeside Athletic",
            "goals_scored": 89,
        },
        {
            "first_name": "Victoria",
            "last_name": "Beasley",
            "team_name": "River City United",
            "goals_scored": 88,
        },
    ]

    explanation = explain_query_results(
        question="Who are the top scorers?",
        interpretation="Find players with the most non-own goals.",
        rows=example_rows,
    )

    print(explanation.answer)