# Step 5 — SQL Safety Gate

## Goal

Create a deterministic validation layer between the LLM and PostgreSQL.

The LLM can propose SQL, but it cannot execute it. The application must parse,
inspect, and approve each proposal before any future database-execution step.

```text
LLM-generated SQL proposal
  → SQL parser
  → deterministic validation rules
      ├─ valid → approved_sql
      └─ invalid or unsafe → validation_errors
```

No model-generated query is executed in this step.

## Why a parser is needed

A parser reads text written in a programming language and checks whether it
follows that language's grammar. A SQL parser turns a query into a structured
representation called an **abstract syntax tree (AST)**.

For example, a parser can identify the selected columns, source tables,
conditions, and ordering in this query:

```sql
SELECT first_name, last_name
FROM players
WHERE position = 'forward'
ORDER BY last_name;
```

This is stronger than looking for keywords in a string. For example, the
following input starts with `SELECT` but contains a second, destructive
statement:

```sql
SELECT * FROM players;
DROP TABLE players;
```

The parser sees two statements, allowing the validator to reject the input.

## Dependency

Step 5 added SQLGlot to `analyst/requirements.txt`:

```text
sqlglot>=28.0
```

SQLGlot parses SQL using the PostgreSQL dialect:

```python
sqlglot.parse(sql, read="postgres")
```

Using the PostgreSQL dialect matters because SQL syntax varies across database
systems.

## Validation module

The deterministic validator lives in [sql_validator.py](sql_validator.py). It
is regular Python code. It does not use an LLM, LangGraph, or a PostgreSQL
connection.

Its input and output are:

```text
SQL text → SqlValidationResult
```

## Validation result

```python
class SqlValidationResult(BaseModel):
    is_valid: bool
    errors: list[str]
    referenced_tables: list[str]
```

Every validation attempt returns the same shape.

A valid result might look like:

```python
{
    "is_valid": True,
    "errors": [],
    "referenced_tables": ["goals", "players", "teams"],
}
```

An invalid result explains why it was rejected instead of silently failing.

## Rules enforced by `validate_sql()`

### Reject empty SQL

```python
if not sql.strip():
```

An empty string, or one containing only whitespace, cannot be approved.

### Require valid PostgreSQL syntax

The validator calls the PostgreSQL parser inside a `try` block:

```python
try:
    statements = sqlglot.parse(sql, read="postgres")
except ParseError as error:
    ...
```

If SQL grammar is invalid, it returns `is_valid=False` and preserves the parser
error for inspection.

This caught the LLM's previous malformed clause:

```sql
ORDER BYgoals_scored DESC
```

The missing space makes `BYgoals_scored` an unexpected token, so the query was
rejected before it could reach PostgreSQL.

### Allow exactly one statement

```python
if len(statements) != 1:
```

This prevents compound input such as a safe-looking `SELECT` followed by a
`DROP`, `DELETE`, or other second statement.

### Allow only read queries containing `SELECT`

```python
if (
    not isinstance(statement, exp.Query)
    or statement.find(exp.Select) is None
):
    errors.append("Only SELECT queries are allowed.")
```

This rejects statement types such as `INSERT`, `UPDATE`, `DELETE`, `CREATE`,
`ALTER`, and `DROP`.

### Reject `SELECT INTO`

`SELECT INTO` can appear to be a read query while creating a new table:

```sql
SELECT * INTO copied_players FROM players;
```

The validator explicitly rejects any parsed `INTO` expression.

### Whitelist accessible tables

`ALLOWED_TABLES` lists the football tables and read-only analytical views that
the analyst may reference:

```text
seasons, teams, players, matches, goals, lineups, cards,
substitutions, player_match_stats, player_rolling_form, season_standings
```

The parser extracts table references structurally:

```python
table.name.lower()
for table in statement.find_all(exp.Table)
```

Any referenced table outside the whitelist is rejected. This prevents a future
LLM from querying unrelated tables, even if one is added to the same database.

### Support CTEs

A common table expression (CTE) is a temporary, query-local name:

```sql
WITH player_goals AS (...) 
SELECT * FROM player_goals;
```

`player_goals` is not a real database table. The validator collects CTE aliases
and treats them as allowed local names, while continuing to validate the real
tables used inside the CTE.

## Standalone validator tests

Running:

```bash
python analyst/sql_validator.py
```

tested five examples without contacting the database:

| Example | Expected result | Observed result |
|---|---|---|
| Valid top-scorers `SELECT` | Approved | Approved |
| `ORDER BYgoals_scored` syntax error | Rejected | Rejected by parser |
| `SELECT` plus `DROP TABLE` | Rejected | Rejected as multiple statements |
| `DELETE FROM players` | Rejected | Rejected as non-`SELECT` |
| Querying `secret_payroll` | Rejected | Rejected as unknown table |

The duplicate error for `DELETE` was removed by combining two overlapping
checks into one read-query rule.

## Integrating validation into LangGraph

Step 4 ended after the LLM generated a proposal. Step 5 added the
`validate_generated_sql` node to [main.py](main.py):

```python
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
```

This node reads only untrusted `proposed_sql`. It always records the validation
result. It creates `approved_sql` only when every validation rule passes.

The workflow is now:

```text
START → normalise_question
             ├─ generate_sql
             │    → validate_generated_sql
             │    → END
             └─ ask_for_clarification → END
```

The state now has these additional fields:

```text
sql_is_valid
validation_errors
referenced_tables
approved_sql
```

## Successful end-to-end validation

The graph generated a new top-scorers proposal and passed it through the safety
gate.

The final state contained:

```text
sql_is_valid: True
validation_errors: []
referenced_tables: [goals, players, teams]
approved_sql: <the validated SELECT query>
```

This demonstrates the distinction between two state values:

```text
proposed_sql  → untrusted text produced by the LLM
approved_sql  → text accepted by deterministic validation rules
```

## Defence in depth

The application now has two separate protections:

```text
1. Application layer
   SQL parser, single-statement rule, SELECT-only rule, SELECT INTO rule,
   and football-table whitelist.

2. Database layer
   The football_analyst PostgreSQL account has read-only permissions and cannot
   INSERT, UPDATE, DELETE, or alter the schema.
```

Neither layer alone should be treated as perfect. Together they substantially
reduce the risk of allowing LLM-generated SQL to cause unwanted database
changes.

## Step 5 outcome

The LangGraph workflow now converts an LLM proposal into an approved query only
after deterministic syntax, statement-type, and table-access checks. The next
step can safely introduce a database-execution node that accepts `approved_sql`
and returns real query rows.
