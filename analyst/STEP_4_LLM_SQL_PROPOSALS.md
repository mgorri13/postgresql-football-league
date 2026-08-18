# Step 4 — LLM-Generated SQL Proposals

## Goal

Add an LLM to the LangGraph workflow so that a natural-language football
question becomes a **structured SQL proposal**.

At the end of this step, the application can:

```text
Question
  → normalise question
  → decide whether clarification is required
  → call the LLM
  → store an interpretation and proposed SQL in graph state
```

The proposed SQL is only text at this stage. It is not sent to PostgreSQL and
is not trusted as valid or safe.

## Dependencies and API key

Step 4 added these direct application dependencies:

```text
langchain-openai>=1.0,<2.0
pydantic>=2.0,<3.0
```

`langchain-openai` provides `ChatOpenAI`, the LangChain integration used to
call an OpenAI model. Pydantic defines and validates the shape of structured
model output.

The OpenAI API key is stored locally in `analyst/.env`:

```text
OPENAI_API_KEY=<private value>
```

The key must never be committed, pasted into source code, or shared. The
project's `.gitignore` excludes `.env` files.

The safe template file `analyst/.env.example` should also list this required
setting with a placeholder:

```text
OPENAI_API_KEY=replace_with_your_openai_api_key
```

## First API connection test

`analyst/llm_check.py` performed the first minimal LLM request:

```python
llm = ChatOpenAI(model="gpt-5.6-terra")
response = llm.invoke("Reply with exactly: LLM connection successful.")
print(response.text)
```

This test confirmed that:

- `OPENAI_API_KEY` was successfully loaded from `.env`;
- Python could communicate with the OpenAI API;
- the selected model was available to the API account;
- the `langchain-openai` package was installed correctly.

`ChatOpenAI(...)` prepares a model client. The actual API request occurs only
when `.invoke(...)` is called.

## Model choice

The application uses:

```text
gpt-5.6-terra
```

This is the balanced GPT-5.6 option, intended for strong performance at a lower
price than the flagship model. It is a suitable starting point for structured
SQL generation while learning. Model choice should later be evaluated against
representative questions, quality, latency, and cost.

## The standalone SQL generator

The LLM helper lives in [sql_generator.py](sql_generator.py). It is an ordinary
Python module, not a LangGraph graph by itself.

Its responsibility is narrowly defined:

```text
Question string → OpenAI model → SqlProposal Python object
```

It does not connect to PostgreSQL and it does not execute SQL.

### Schema context

The `DATABASE_SCHEMA` string describes the database tables and columns that the
model is allowed to use:

```text
seasons, teams, players, matches, goals, lineups, player_match_stats
```

The model cannot inspect the actual database merely by being called. The schema
context gives it the information needed to construct a query. This first schema
description is intentionally concise; it can be expanded with further tables,
views, relationships, and domain rules later.

### Structured output with Pydantic

`SqlProposal` defines the only shape accepted from the model:

```python
class SqlProposal(BaseModel):
    interpretation: str
    sql: str
```

The output looks conceptually like this:

```python
SqlProposal(
    interpretation="The user wants the five players with the highest goal counts.",
    sql="SELECT ..."
)
```

The model is wrapped with:

```python
structured_llm = llm.with_structured_output(
    SqlProposal,
    method="json_schema",
)
```

This asks OpenAI for native structured output matching the Pydantic schema.
It avoids fragile parsing of conversational text such as “Here is some SQL you
can try…” and gives the application named fields it can process predictably.

### Prompt constraints

`generate_sql_proposal(question)` builds a prompt containing:

- the schema context;
- the user question;
- instructions to return one PostgreSQL `SELECT` or `WITH ... SELECT` query;
- instructions not to use write or schema-changing statements;
- instructions not to claim the query has been executed.

The function calls:

```python
return structured_llm.invoke(prompt)
```

This is the API request. It returns a validated `SqlProposal` object.

Prompt rules guide model behaviour, but they are not a security boundary. The
application must still validate every generated query before it can execute.

## Integrating the LLM into LangGraph

The original graph had a placeholder answer node. Step 4 replaced that normal
path with the `generate_sql` node in [main.py](main.py).

```python
def generate_sql(state: AnalystState) -> dict:
    proposal = generate_sql_proposal(state["normalised_question"])

    return {
        "interpretation": proposal.interpretation,
        "proposed_sql": proposal.sql,
    }
```

This node:

1. Reads `normalised_question` from the existing graph state.
2. Calls the ordinary Python LLM helper.
3. Returns two updates for LangGraph to merge into state.

The state schema now includes two optional fields that are not present at the
start of a run:

```python
interpretation: NotRequired[str]
proposed_sql: NotRequired[str]
```

The current graph topology is:

```text
START → normalise_question
             ├─ generate_sql → END
             └─ ask_for_clarification → END
```

Questions containing both `best` and `team` take the clarification route. All
other questions take the LLM route. This keyword rule is only a small
deterministic teaching example; it will not understand all valid English
phrasings.

## Observing the completed run

`graph.stream(..., stream_mode="values", version="v2")` prints a full state
snapshot after each step.

For this question:

```text
Who are the five top scorers in the league?
```

the state evolved as follows:

```text
Initial state
  question

After normalise_question
  question + normalised_question

After generate_sql
  question + normalised_question + interpretation + proposed_sql
```

The observed proposal correctly used the `goals`, `players`, and `teams`
tables, grouped goal counts by player, sorted them, and limited the result to
five rows. It also deliberately excluded own goals, a reasonable football
statistics decision.

However, it contained this syntax error:

```sql
ORDER BYgoals_scored DESC
```

The missing space makes the SQL invalid. The model also interpreted “in the
league” as “across all generated seasons,” even though the user did not specify
a season. This confirms two important facts:

```text
LLM-generated SQL is a proposal, not a guarantee of valid SQL.
LLM-generated interpretation is a proposal, not automatically the user's intent.
```

This is why the query was not executed in Step 4.

## Step 4 outcome

The project now has a LangGraph node that uses an LLM to translate a question
into a structured interpretation and SQL proposal. The generated SQL remains
untrusted and is stored only in workflow state, ready for deterministic
validation in Step 5.
