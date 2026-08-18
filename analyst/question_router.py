from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


load_dotenv(Path(__file__).with_name(".env"))


class QuestionAssessment(BaseModel):
    needs_clarification: bool = Field(
        description=(
            "Whether the user must clarify their question before "
            "a reliable SQL query can be generated."
        )
    )
    clarification_question: str | None = Field(
        description=(
            "One concise clarification question if clarification is needed; "
            "otherwise null."
        )
    )


llm = ChatOpenAI(model="gpt-5.6-terra")

structured_llm = llm.with_structured_output(
    QuestionAssessment,
    method="json_schema",
)


def assess_question(question: str) -> QuestionAssessment:
    prompt = f"""
You decide whether a user question about a fictional football-league database
needs clarification before SQL can answer it accurately.

The database contains many seasons.

Ask for clarification only when a missing choice would materially change the
answer. Examples:
- "Which team is the best?" is ambiguous because "best" could mean most
  points, best goal difference, or best recent form.
- "Who was the best team this season?" also needs a specific season and a
  definition of "best".
- "Who are the five top scorers of all time?" is clear enough.

If clarification is needed:
- set needs_clarification to true;
- ask exactly one concise, useful question.

If clarification is not needed:
- set needs_clarification to false;
- set clarification_question to null.

User question:
{question}
"""

    return structured_llm.invoke(prompt)


if __name__ == "__main__":
    clear_question = assess_question(
        "Who are the five top scorers of all time?"
    )
    print(clear_question)

    ambiguous_question = assess_question(
        "Which team is the best?"
    )
    print(ambiguous_question)