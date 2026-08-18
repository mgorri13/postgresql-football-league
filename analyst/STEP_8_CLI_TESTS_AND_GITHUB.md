# Step 8 — Command-Line App, Tests, and GitHub Readiness

## Goal

Turn the LangGraph learning workflow into a small, usable application and make it easier for another developer or recruiter to run, inspect, and trust.

At the end of this step, the football database analyst has:

1. a clean command-line interface (CLI);
2. an optional debug mode that shows the LangGraph state after each node;
3. a simple multi-turn clarification loop in the terminal;
4. automated tests for SQL safety and graph routing;
5. a safe `.env.example` file; and
6. a GitHub-ready project README.

## Part 1 — Separating the graph from the user interface

Before Step 8, `main.py` ended with a hard-coded test question and this kind of loop:

```python
input_state = {
    "question": "Who are the five top scorers in the league?"
}

for event in graph.stream(...):
    print(event["data"])
```

This was useful while learning because it showed every state snapshot. It was not a good experience for a normal user because the user had to edit Python code to change the question and read large dictionaries to find the answer.

The LangGraph graph itself stays the same. Step 8 changes how a person supplies a question and sees the result.

## Part 2 — Command-line arguments with `argparse`

We added:

```python
import argparse
from pprint import pprint
```

`argparse` is built into Python. It reads command-line options such as:

```bash
python analyst/main.py "Who are the five top scorers of all time?"
```

and:

```bash
python analyst/main.py --debug "Which team is the best?"
```

`pprint` means “pretty print.” It formats nested dictionaries in a more readable way than normal `print()`.

The `parse_arguments()` function creates two inputs:

```python
question
```

The words of the user’s question.

```python
--debug
```

A Boolean switch. It is `False` normally and becomes `True` when the user includes `--debug`.

## Part 3 — `invoke()` for normal users and `stream()` for developers

The CLI uses two different ways to run the same graph.

### Normal mode

```python
graph.invoke(input_state)
```

`invoke()` runs the complete graph and returns only the final state. The CLI then prints only:

```python
final_state["answer"]
```

That gives a clean result such as:

```text
Answer:
The five all-time top scorers are ...
```

### Debug mode

```python
graph.stream(
    input_state,
    stream_mode="values",
    version="v2",
)
```

`stream()` yields the state after every node. In debug mode, the program uses:

```python
pprint(event["data"])
```

This lets a developer inspect the graph’s work in sequence:

```text
question
-> normalised_question
-> clarification assessment
-> SQL proposal
-> validation result
-> database rows
-> answer
```

For an ambiguous question, debug mode proves that the graph stops early:

```text
question
-> normalise_question
-> assess_user_question
-> ask_for_clarification
-> END
```

In this case, it does not produce SQL or contact PostgreSQL.

## Part 4 — The CLI entry point

We used this Python convention:

```python
if __name__ == "__main__":
    main()
```

It means:

```text
Run the command-line program only when Python executes main.py directly.
```

When another file, such as a test file, imports `main.py`, Python does not start the terminal app. It only makes the graph and its functions available to import.

That behaviour makes testing possible.

## Part 5 — Interactive clarification loop

The first CLI version accepted one question and then ended. If it asked:

```text
Which season should the top scorers be taken from?
```

and the user typed a response after the program had ended, the terminal treated that response as a shell command and displayed `command not found`.

We added `run_conversation()` to handle this situation.

Its logic is:

```text
Run question
-> print answer
-> if no clarification is needed, finish
-> otherwise ask the user for clarification
-> combine original question and clarification
-> run the graph again
```

For example:

```text
Original question: Which team is the best?
User clarification: Most points in the third season.
```

The second graph run receives both pieces of context and can continue to SQL generation.

This is a lightweight conversational loop. It does not yet store a persistent LangGraph conversation thread or checkpoint. It is suitable for the CLI and gives users a natural way to answer one clarification request.

## Part 6 — User-friendly error handling

The CLI catches two broad situations:

```python
except KeyboardInterrupt:
```

This handles Ctrl+C, allowing the user to cancel gracefully.

```python
except Exception as error:
```

This prevents an unexpected error from being presented as an unhelpful wall of text in normal mode. In debug mode the program raises the original error so the developer can inspect the full traceback.

## Part 7 — Automated testing with pytest

We added pytest to `requirements.txt`:

```text
pytest>=8.0,<10.0
```

It was installed with:

```bash
python -m pip install -r analyst/requirements.txt
```

Tests run with:

```bash
python -m pytest -q
```

`-q` means quiet mode: show a concise result rather than verbose output.

The successful result was:

```text
12 passed
```

### What is a test?

A test is an automatic statement of expected behaviour. For example:

```python
result = validate_sql("DELETE FROM players;")

assert result.is_valid is False
```

This means:

```text
When the validator receives DELETE, it must reject it.
```

If a future code change accidentally allows `DELETE`, this assertion fails immediately.

### SQL validator tests

`analyst/test_sql_validator.py` contains five tests.

| Case | Expected result |
| --- | --- |
| Safe `SELECT` | Accepted |
| Multiple SQL statements | Rejected |
| `DELETE` query | Rejected |
| Unallowed table | Rejected |
| SQL syntax error | Rejected |

These tests call the real `validate_sql()` function directly. They do not call OpenAI, PostgreSQL, or Docker. This makes them fast, deterministic, and free to run.

### Graph routing tests

`analyst/test_graph_routing.py` contains seven tests for the functions that decide the next LangGraph node.

For example:

```python
state = {
    "sql_is_valid": False,
    "repair_count": 0,
}

assert choose_after_validation(state) == "repair_sql"
```

In plain language:

```text
Invalid SQL plus zero repairs used -> route to repair_sql.
```

The tests verify:

| Situation | Expected route |
| --- | --- |
| Ambiguous question | `ask_for_clarification` |
| Clear question | `generate_sql` |
| Invalid SQL, no repair used | `repair_sql` |
| Invalid SQL, repair used | `report_validation_failure` |
| Execution error, no repair used | `repair_sql` |
| Execution error, repair used | `report_query_failure` |
| Successful execution | `explain_results` |

These tests prove the graph cannot repair forever because the maximum repair count is enforced.

### Why `conftest.py` exists

The application files and test files are currently both in `analyst/`.

`analyst/conftest.py` adds the `analyst/` directory to Python’s module search path:

```python
sys.path.insert(0, str(ANALYST_DIRECTORY))
```

This allows test files to import functions from `main.py` without starting the CLI.

## Part 8 — Safe environment template

We completed `.env.example` with placeholders for both database access and OpenAI:

```text
FOOTBALL_DB_HOST=127.0.0.1
FOOTBALL_DB_PORT=5432
FOOTBALL_DB_NAME=football_league
FOOTBALL_DB_USER=football_analyst
FOOTBALL_DB_PASSWORD=replace_with_your_local_password
OPENAI_API_KEY=replace_with_your_openai_api_key
```

The real `analyst/.env` contains secrets and must stay ignored by Git. `.env.example` contains only safe placeholder text and should be committed so other developers know which variables they need.

## Part 9 — GitHub README

We added a dedicated `analyst/README.md` rather than replacing the root README of the wider football SQL project.

The README explains:

- what the analyst does;
- its LangGraph architecture;
- safety protections;
- prerequisites and setup;
- how to run normal, interactive, and debug modes;
- how to run tests;
- project file structure; and
- future improvements.

This makes the analyst understandable as a standalone portfolio project within the larger football database repository.

## Commands to remember

Activate the environment:

```bash
source analyst/.venv/bin/activate
```

Run a direct question:

```bash
python analyst/main.py "Who are the five top scorers of all time?"
```

Start interactive mode:

```bash
python analyst/main.py
```

Inspect graph state in debug mode:

```bash
python analyst/main.py --debug "Which team is the best?"
```

Run tests:

```bash
python -m pytest -q
```

## What Step 8 demonstrates for a portfolio

The project is now not only a technical experiment. It has a usable interface, test coverage, documentation, and a clear security story.

It demonstrates:

- Python CLI design;
- LangGraph state inspection and conditional routes;
- separation between user mode and developer debug mode;
- safe, bounded retry logic;
- automated safety and routing tests;
- environment-variable secret handling; and
- documentation designed for reproducibility.

## Next step

The next stage can add a simple Streamlit web interface and deploy the app to a server.

Before deployment, the server needs access to the PostgreSQL database. A recommended setup is Docker Compose running the database and app together, exposing only the webpage—not PostgreSQL—to the public internet.
