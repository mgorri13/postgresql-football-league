# Step 6 — Execute Safe SQL and Explain the Result

## Goal

Turn a validated SQL proposal into a trustworthy answer for a football question.

At the end of this step, the project can:

1. receive a natural-language question;
2. ask an LLM to propose SQL;
3. validate the proposal before it touches PostgreSQL;
4. execute only approved SQL through a restricted, read-only database connection;
5. collect real database rows; and
6. ask a second LLM to explain only those rows in clear language.

The crucial principle is that **PostgreSQL provides the facts; the final LLM only explains them**.

## The successful workflow

```text
User question
  -> normalise_question
  -> generate_sql
  -> validate_generated_sql
  -> execute_approved_sql
  -> explain_results
  -> END
```

The graph also has safe failure paths:

```text
Question needs clarification
  -> ask_for_clarification
  -> END

SQL fails safety validation
  -> report_validation_failure
  -> END

SQL is safe but PostgreSQL cannot execute it
  -> report_query_failure
  -> END
```

## Part 1 — A safe execution doorway in `database.py`

We added `execute_approved_query(sql)` to `database.py`.

```python
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
```

### Why validate a second time?

The LangGraph node already validates generated SQL, but `database.py` validates it again. This is **defence in depth**: the database function refuses unsafe SQL even if another future part of the program accidentally calls it directly.

### Why `fetchmany(MAX_RESULT_ROWS)`?

`MAX_RESULT_ROWS = 100` prevents a question from sending an enormous query result to the terminal or to the final LLM. It does not change data in the database; it limits what the application reads back.

### Why is the database still protected?

The PostgreSQL connection already uses the `football_analyst` account. That account inherits read-only permissions. The connection also sets:

```text
default_transaction_read_only=on
statement_timeout=5000
```

So the project has several protections working together:

1. SQL validator: allows one safe `SELECT` query using known tables.
2. Python execution function: validates again and limits returned rows.
3. PostgreSQL role: only has read permissions.
4. Read-only transaction: prevents writes during the connection.
5. Five-second timeout: avoids a long-running query taking too long.

## Part 2 — New state fields

We added these optional fields to `AnalystState` in `main.py`:

```python
query_rows: NotRequired[list[dict]]
query_error: NotRequired[str]
```

- `query_rows` stores the actual records returned by PostgreSQL.
- `query_error` stores a database error if execution fails.

The fields are optional because they do not exist at the beginning of every graph run. They are created later by the execution node.

## Part 3 — The `execute_approved_sql` node

```python
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
    }
```

This node has one responsibility: execute `approved_sql` and place the result in the state.

`psycopg.Error` represents a PostgreSQL-related error. For example, a query may be a safe `SELECT` but still reference a column that does not exist. Rather than crashing immediately, the node writes an error into the state so LangGraph can route to a useful response.

## Part 4 — Explaining real rows with a second LLM

We created `result_explainer.py` with an `explain_query_results()` function.

It receives only:

- the normalized user question;
- the interpretation produced earlier; and
- the `query_rows` returned by PostgreSQL.

It does **not** receive database credentials and it does **not** execute SQL or browse the database.

```text
First LLM:  question -> proposed SQL
Validator:  proposed SQL -> approved or rejected
PostgreSQL: approved SQL -> factual rows
Second LLM: factual rows -> readable answer
```

The results are converted to JSON before being sent to the final LLM:

```python
rows_as_json = json.dumps(rows, indent=2, default=str)
```

`default=str` makes the conversion work even if a future result contains values such as dates or decimals.

The result explainer uses a Pydantic model:

```python
class ResultExplanation(BaseModel):
    answer: str
```

Structured output ensures the Python code receives a predictable object with an `answer` field instead of having to guess how to read free-form model output.

## Part 5 — The `explain_results` node

```python
def explain_results(state: AnalystState) -> dict:
    explanation = explain_query_results(
        question=state["normalised_question"],
        interpretation=state["interpretation"],
        rows=state["query_rows"],
    )

    return {
        "answer": explanation.answer,
    }
```

This is a regular LangGraph node. It reads the previous nodes' state and returns a partial update. LangGraph merges the returned `answer` into the shared state.

## Part 6 — Routing after execution

After SQL execution, the graph must decide whether it has rows to explain or an execution error to report.

```python
def choose_after_execution(state: AnalystState) -> str:
    if "query_error" in state:
        return "report_query_failure"

    return "explain_results"
```

This function is a **routing function**, not a node. It does not update the state. It returns the name of the node that should run next.

The matching conditional edges are:

```python
builder.add_conditional_edges(
    "execute_approved_sql",
    choose_after_execution,
    {
        "explain_results": "explain_results",
        "report_query_failure": "report_query_failure",
    },
)
```

## Example run

For the question:

```text
Who are the five top scorers in the league?
```

PostgreSQL returned these real rows:

| Rank | Player | Team | Non-own goals |
| --- | --- | --- | ---: |
| 1 | Ashley Collins | Lakeside Athletic | 89 |
| 2 | Victoria Beasley | River City United | 88 |
| 3 | Brian Ochoa | Eastwood Rovers | 87 |
| 4 | Melissa Freeman | Northbridge FC | 84 |
| 5 | David Bell | Northbridge FC | 80 |

The final LLM then created a readable answer using those rows. It did not independently search the whole database.

## `stream()` versus `invoke()`

During development, `main.py` uses:

```python
graph.stream(...)
```

This prints a snapshot of the entire state after every node. It is excellent for learning because you can see fields appear in sequence:

```text
question
-> normalised_question
-> interpretation and proposed_sql
-> validation fields and approved_sql
-> query_rows
-> answer
```

For the normal application experience, use:

```python
final_state = graph.invoke(input_state)
print(final_state["answer"])
```

`invoke()` runs the whole graph and returns only the final state, so the terminal displays the concise answer instead of debugging snapshots.

## What Step 6 proves for the portfolio

This is no longer a demo that simply asks an LLM a football question. It is an agentic data workflow with:

- stateful graph orchestration with LangGraph;
- conditional routing;
- LLM-based SQL generation with structured output;
- SQL parsing and allow-list validation;
- a restricted PostgreSQL role and read-only connection;
- execution-error handling;
- result limits; and
- grounded natural-language explanations of real query data.

## Known limitations to improve next

1. A syntactically valid query can still use a wrong column or interpret a question poorly.
2. The graph currently reports a database error rather than repairing the query.
3. The clarification rule is intentionally simple: it looks for the words `best` and `team`.
4. "The league" is currently interpreted as all recorded seasons unless the user specifies a season.
5. The terminal is still the user interface.

The next step addresses the first three limitations.
