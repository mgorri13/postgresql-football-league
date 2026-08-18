# Step 7 — Controlled SQL Repair and Intelligent Clarification

## Goal

Make the LangGraph workflow resilient when an LLM proposal is wrong or when a user question is too ambiguous to answer reliably.

At the end of this step, the analyst can:

1. make one controlled attempt to repair invalid or unexecutable SQL;
2. validate every repaired query again before it can reach PostgreSQL;
3. avoid infinite repair loops;
4. preserve the intended result shape while repairing SQL; and
5. use an LLM-based routing decision to ask a useful clarification question before generating SQL when needed.

## The two reliability problems

### 1. A proposed query can fail

An LLM can create SQL that looks plausible but is wrong in two different ways:

- **Validation failure:** the SQL parser rejects it, it uses an unallowed table, it contains multiple statements, or it is not a `SELECT` query.
- **Database execution failure:** the SQL is structurally safe but PostgreSQL rejects it, for example because it names a column that does not exist.

Before this step, either failure ended the graph with an error message.

### 2. A user question can be ambiguous

The old graph used a narrow Python keyword rule:

```python
if "best" in question and "team" in question:
    return "ask_for_clarification"
```

It could not recognize equivalent wording such as:

```text
Which club performed best?
Who had the strongest season?
Which team was best this season?
```

## Part 1 — Bounded SQL repair

### The repair limit

In `main.py`, we added:

```python
MAX_REPAIR_ATTEMPTS = 1
```

This is a deliberate safety and cost boundary. The application can make:

- one initial SQL proposal; and
- at most one repair proposal.

It cannot keep calling the LLM indefinitely if a query continues to fail.

The state tracks this with:

```python
repair_count: NotRequired[int]
```

The helper function is:

```python
def can_attempt_repair(state: AnalystState) -> bool:
    return state.get("repair_count", 0) < MAX_REPAIR_ATTEMPTS
```

`state.get("repair_count", 0)` means: use the current count if it exists; otherwise treat it as zero on the first pass.

### The repair LLM function

We added `repair_sql_proposal()` to `sql_generator.py`.

It receives four pieces of context:

```text
1. Original user question
2. Intended interpretation of that question
3. Previous failed SQL
4. Precise validation or PostgreSQL error feedback
```

It returns the same structured `SqlProposal` model already used for initial SQL generation:

```python
class SqlProposal(BaseModel):
    interpretation: str
    sql: str
```

Using the same output model is useful because both the initial proposal and repair proposal have the same contract: an interpretation plus one SQL string.

### Why include the intended interpretation?

The first repair test fixed the invalid `player_name` column but returned fewer fields than the original proposal. The original intention included player names, teams, and totals; the repaired query initially omitted team names.

The repair prompt was improved to include:

```text
Original intended interpretation:
Find the five players with the most non-own goals,
including their names, teams, and goal totals.
```

It now explicitly instructs the model to:

```text
- Preserve the intended interpretation and all requested output fields.
- Make the smallest correction needed to fix the reported problem.
```

This separates two important ideas:

- **Safety:** Is the SQL allowed to run?
- **Quality:** Does the SQL still answer the question the user asked?

The SQL validator handles safety. Context and evaluation improve quality.

### The `repair_sql` LangGraph node

`main.py` contains a node with this responsibility:

```python
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
```

The node does not execute SQL. It only creates a new proposal and records that one repair was used.

### Why clear `query_error`?

`query_error` was changed to:

```python
query_error: NotRequired[str | None]
```

After a failed query, the state contains an error string. Before testing the repaired proposal, `repair_sql` sets it to `None`.

On successful database execution, `execute_approved_sql` also returns:

```python
{
    "query_rows": rows,
    "query_error": None,
}
```

Otherwise an old error could stay in the shared state and make the graph incorrectly take the failure route even after a successful repair.

For the same reason, the execution router uses:

```python
if state.get("query_error"):
```

rather than:

```python
if "query_error" in state:
```

The second version only checks whether the key exists. The first checks whether its value is a real, non-empty error.

## Part 2 — Repair routes in the graph

Both kinds of failure can route to `repair_sql`.

```text
Initial proposal
  -> validate_generated_sql
       -> valid: execute_approved_sql
       -> invalid, repair available: repair_sql
       -> invalid, repair exhausted: report_validation_failure

Execution
  -> success: explain_results
  -> error, repair available: repair_sql
  -> error, repair exhausted: report_query_failure

Repair
  -> validate_generated_sql
```

The repair edge is deliberately:

```python
builder.add_edge("repair_sql", "validate_generated_sql")
```

There is no edge from `repair_sql` directly to the database. A repaired query must go through the same safety gate as the first query.

## Evidence: database execution-error repair

We temporarily returned this safe-looking but invalid SQL from `generate_sql`:

```sql
SELECT player_name FROM players LIMIT 5;
```

The SQL validator accepted it because:

- it was one `SELECT` statement;
- it used the allowed `players` table; and
- it did not contain a forbidden write operation.

PostgreSQL then returned:

```text
column "player_name" does not exist
```

The graph state showed:

```python
"query_error": 'column "player_name" does not exist ...'
```

The repair node then produced a new query and state showed:

```python
"repair_count": 1
```

The repaired query was validated, executed, and explained successfully.

## Evidence: preserving result shape during repair

We repeated the controlled test with this intended interpretation:

```text
Find the five players with the most non-own goals,
including their names, teams, and goal totals.
```

The repaired query joined `goals`, `players`, and `teams`, returning:

```text
first_name, last_name, team_name, goal_total
```

The final answer included all intended fields:

```text
1. Ashley Collins (Lakeside Athletic) — 89 goals
2. Victoria Beasley (River City United) — 88 goals
...
```

## Part 3 — Intelligent clarification routing

We created `question_router.py`.

Its job is limited and specific: assess whether the user must clarify their question before SQL generation can proceed accurately.

It does not access PostgreSQL and it does not write SQL.

### Structured decision model

```python
class QuestionAssessment(BaseModel):
    needs_clarification: bool
    clarification_question: str | None
```

Examples:

```python
QuestionAssessment(
    needs_clarification=False,
    clarification_question=None,
)
```

```python
QuestionAssessment(
    needs_clarification=True,
    clarification_question=(
        "Do you mean most points, best goal difference, or best recent form?"
    ),
)
```

The `str | None` type allows the field to be explicitly `None` for a clear question. Structured-output schemas require every field to be present, but a field can use `null` where appropriate.

### New state fields

```python
needs_clarification: NotRequired[bool]
clarification_question: NotRequired[str | None]
```

### The assessment node

```python
def assess_user_question(state: AnalystState) -> dict:
    assessment = assess_question(state["normalised_question"])

    return {
        "needs_clarification": assessment.needs_clarification,
        "clarification_question": assessment.clarification_question,
    }
```

The node calls `question_router.py` and writes the resulting decision into LangGraph state.

### Routing after assessment

```python
def choose_after_assessment(state: AnalystState) -> str:
    if state["needs_clarification"]:
        return "ask_for_clarification"

    return "generate_sql"
```

`choose_after_assessment` is a routing function. It reads state and returns the name of the next node. It does not itself update state.

### Dynamic clarification answer

The clarification node no longer uses one fixed sentence. It reads the LLM-created question:

```python
def ask_for_clarification(state: AnalystState) -> dict:
    question = state["clarification_question"]

    if question is None:
        question = "Please clarify what you would like to know."

    return {"answer": question}
```

The fallback is defensive programming: it ensures the user still receives a helpful response if a future implementation somehow marks a question ambiguous without supplying a question.

## New graph beginning

```text
START
  -> normalise_question
  -> assess_user_question
       -> needs clarification: ask_for_clarification -> END
       -> clear question: generate_sql
```

The full successful workflow is now:

```text
START
  -> normalise_question
  -> assess_user_question
  -> generate_sql
  -> validate_generated_sql
  -> execute_approved_sql
  -> explain_results
  -> END
```

## Evidence: clarification test

For:

```text
Which team is the best?
```

the graph followed:

```text
normalise_question
-> assess_user_question
-> ask_for_clarification
-> END
```

It did not create `proposed_sql`, `approved_sql`, or `query_rows`. This proves that an ambiguous question is stopped before the database stage.

## Evidence: clear-question test

For:

```text
Who are the five top scorers in the league?
```

the state contained:

```python
"needs_clarification": False
"clarification_question": None
```

The graph then generated safe SQL, returned real PostgreSQL rows, and produced the final ranked answer. This proves the assessment node does not block a clear question unnecessarily.

## What Step 7 demonstrates for a portfolio

The project now demonstrates more than a straight-line chain. It includes:

- a stateful LangGraph loop;
- bounded retries with an explicit counter;
- error-aware conditional routing;
- repeated validation before every database execution;
- structured LLM decisions;
- LLM-assisted clarification before expensive or unsafe work; and
- separation of safety checks, database facts, and LLM language tasks.

## Current limitations

1. The clarification result ends the current run; a later step can persist state and resume after the user responds.
2. The prompt can improve over time with real examples and automated evaluation cases.
3. The terminal still prints full debug state rather than acting like a finished user application.
4. We need automated tests that do not spend API credits or depend on variable LLM output.

## Next step

Step 8 will turn the learning prototype into a portfolio-ready application:

1. provide a clean command-line interface using `graph.invoke()`;
2. display only the final answer or clarification question to a user;
3. retain an optional debug mode for state snapshots;
4. add automated tests for validator and routing behaviour without live LLM calls; and
5. start the README and GitHub-ready documentation.
