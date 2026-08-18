# Step 3 — Safe Python Connection to PostgreSQL

## Goal

Connect the football analyst's Python code to the existing `football_league`
PostgreSQL database safely, before allowing an LLM to suggest any SQL.

The outcome is a Python module that:

- connects to PostgreSQL as a restricted application user;
- runs a fixed, hand-written `SELECT` query;
- receives real database rows as Python dictionaries;
- verifies that the account is read-only;
- keeps passwords out of source code and Git.

## Where the connection goes

PostgreSQL is a server process running inside Docker. The Python analyst runs on
the Mac, outside the Docker container.

```text
Mac
  └─ analyst/database.py
       │  PostgreSQL connection over port 5432
       ▼
Docker container: football_league_db
  └─ PostgreSQL server
       └─ football_league database
```

`psycopg.connect(...)` opens this communication channel. Python sends a SQL
query, PostgreSQL executes the query against its data, and PostgreSQL returns
the result rows to Python. Python does not calculate league statistics itself.

## PostgreSQL roles and permissions

PostgreSQL uses **roles** as identities to which permissions can be assigned.
A role can be a login account, a permission group, or both.

The existing migration `012_create_readonly_role.sql` created:

```text
football_readonly
```

This role has `SELECT` permission on the public schema but has `NOLOGIN`, so it
cannot be used directly by an application.

Step 3 added the migration
`migrations/013_create_football_analyst_role.sql`:

```sql
CREATE ROLE football_analyst LOGIN IN ROLE football_readonly;
```

This creates the following permission relationship:

```text
football_analyst
  ├─ can log in
  └─ inherits permissions from football_readonly
       ├─ can SELECT
       └─ cannot INSERT, UPDATE, DELETE, or alter the schema
```

The Python application uses `football_analyst`, never the powerful `postgres`
administrator role. This follows the principle of least privilege: give an
application only the permissions it needs.

The password was set interactively with `\password football_analyst`. It is not
stored in the migration file or committed to Git.

## Docker authentication behaviour

When `psql` was run *inside* the database container with `-h 127.0.0.1`, it did
not ask for the password. The local Docker development configuration uses a
`trust` rule for connections originating within the container.

The analyst runs on the Mac, outside that container. Its connection reaches
PostgreSQL through Docker's published port and is authenticated by the
`scram-sha-256` host rule, which requires the application password.

This local `trust` rule is convenient for development. It is not a production
security configuration.

## Python dependencies

The analyst has its own virtual environment:

```bash
python3 -m venv analyst/.venv
source analyst/.venv/bin/activate
```

Dependencies are recorded in `analyst/requirements.txt`:

```text
langgraph>=1.0,<2.0
psycopg[binary]>=3.0,<4.0
python-dotenv>=1.0,<2.0
```

Install them with:

```bash
python -m pip install -r analyst/requirements.txt
```

`psycopg` is the PostgreSQL driver used by Python. The `[binary]` option
provides the ready-to-use development installation. `python-dotenv` loads
private settings from an `.env` file.

## Private connection settings

`analyst/.env` contains the real local connection settings:

```text
FOOTBALL_DB_HOST=127.0.0.1
FOOTBALL_DB_PORT=5432
FOOTBALL_DB_NAME=football_league
FOOTBALL_DB_USER=football_analyst
FOOTBALL_DB_PASSWORD=<private value>
```

The actual `.env` file is ignored by Git. Never commit it or share its password.

`analyst/.env.example` is safe to commit. It documents the required keys with a
placeholder password so another developer can create their own `.env` file.

## `database.py`

The connection and fixed query code lives in [database.py](database.py).

### Loading configuration

```python
load_dotenv(Path(__file__).with_name(".env"))
```

This loads the `.env` file located beside `database.py`. The values become
available through `os.environ`, for example:

```python
os.environ["FOOTBALL_DB_USER"]
```

### Opening a connection

```python
def get_connection():
    return psycopg.connect(...)
```

This function returns an open connection to the `football_league` database. It
is a reusable helper, avoiding repeated configuration in each query function.

The connection uses two additional session guardrails:

```python
options="-c default_transaction_read_only=on -c statement_timeout=5000"
```

- `default_transaction_read_only=on` makes transactions on this connection
  read-only by default.
- `statement_timeout=5000` stops a query if it runs for more than five seconds.

These are defence-in-depth measures. The restricted PostgreSQL role remains the
stronger protection because it cannot be bypassed by application code.

### Automatic cleanup with `with`

```python
with get_connection() as connection:
    with connection.cursor() as cursor:
        ...
```

The first `with` opens a connection for the indented code and closes it when
the work finishes. The second creates and closes a cursor, which is the object
used to send individual SQL commands. This cleanup also happens if a query
raises an error.

### Returning dictionary rows

```python
row_factory=dict_row
```

This makes each returned PostgreSQL row a dictionary:

```python
{
    "first_name": "Alex",
    "last_name": "Smith",
    "team_name": "Northbridge FC",
    "goals_scored": 42,
}
```

Without it, Python would receive positional tuples, which are harder to read
and easier to misuse.

## Fixed top-scorers query

`get_top_scorers(limit=5)` sends a hand-written query to PostgreSQL. It joins
goals, players, and teams; counts goals by player; sorts the count; and returns
the top rows.

The `LIMIT` value is supplied safely:

```python
cursor.execute(query, (limit,))
```

The query uses `LIMIT %s`, a database parameter placeholder. Python sends the
value separately instead of constructing SQL by concatenating text. This is the
safe pattern for SQL values supplied by an application.

## Verifying the application connection

`check_database_access()` runs a safe `SELECT` query that checks the active
database session:

```text
current_user              → football_analyst
transaction_read_only     → on
can_select                → True
can_insert                → False
```

This confirms that the Python process, not just an administrator in a Docker
terminal, is using the intended restricted identity.

Run the module from the repository root:

```bash
python analyst/database.py
```

The module first prints the access check and then five real top-scorer rows.

## What has not been added yet

- The LangGraph workflow does not call `database.py` yet.
- No LLM is installed or called.
- No SQL is generated from natural-language questions.
- There is no general-purpose query executor exposed to the model.

This order is deliberate. The next stages will add LLM-generated SQL only after
the database connection is known to be correct and locked down.

## Step 3 outcome

The project now has a safe, reproducible database access layer. Python can
retrieve factual football data through a least-privileged account, and the
application is prepared for controlled integration with the LangGraph workflow.
