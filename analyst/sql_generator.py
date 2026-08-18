from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


load_dotenv(Path(__file__).with_name(".env"))


DATABASE_SCHEMA = """
seasons:
  id, name, starts_on, ends_on

teams:
  id, name, city, founded_year

players:
  id, team_id, first_name, last_name, position, date_of_birth

matches:
  id, season_id, home_team_id, away_team_id, played_at, home_score, away_score

goals:
  id, match_id, scorer_id, minute, is_own_goal

lineups:
  match_id, player_id, team_id, is_starting, position

player_match_stats:
  match_id, player_id, minutes_played, rating, shots, passes_completed
"""


class SqlProposal(BaseModel):
    interpretation: str = Field(
        description="A short explanation of what the user's question means."
    )
    sql: str = Field(
        description="One PostgreSQL read-only SQL query that answers the question."
    )


llm = ChatOpenAI(model="gpt-5.6-terra")

structured_llm = llm.with_structured_output(
    SqlProposal,
    method="json_schema",
)


def generate_sql_proposal(question: str) -> SqlProposal:
    prompt = f"""
You generate PostgreSQL SQL proposals for a fictional football-league database.

Database schema:
{DATABASE_SCHEMA}

Rules:
- Return exactly one PostgreSQL SELECT query, or one WITH ... SELECT query.
- Use only the tables and columns provided in the schema.
- Do not use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, COPY, or multiple statements.
- Do not use Markdown code fences.
- Do not claim that you executed the query or know its result.

User question:
{question}
"""

    return structured_llm.invoke(prompt)

def repair_sql_proposal(
    question: str,
    intended_interpretation: str,
    failed_sql: str,
    error_feedback: str,
) -> SqlProposal:
    prompt = f"""
You repair PostgreSQL SQL proposals for a fictional football-league database.

Database schema:
{DATABASE_SCHEMA}

Original user question:
{question}

Original intended interpretation:
{intended_interpretation}

The previous SQL proposal:
{failed_sql}

Feedback explaining why it failed:
{error_feedback}

Return a corrected proposal.

Rules:
- Return exactly one PostgreSQL SELECT query, or one WITH ... SELECT query.
- Use only the tables and columns provided in the schema.
- Correct the specific problem described in the feedback.
- Do not use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, COPY, or multiple statements.
- Do not use Markdown code fences.
- Do not claim that you executed the query or know its result.
- Preserve the intended interpretation and all requested output fields.
- Make the smallest correction needed to fix the reported problem.
"""

    return structured_llm.invoke(prompt)

if __name__ == "__main__":
    proposal = generate_sql_proposal(
        "Who are the five top scorers in the league?"
    )

    print("Interpretation:")
    print(proposal.interpretation)

    print("\nProposed SQL:")
    print(proposal.sql)