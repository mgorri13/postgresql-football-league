# PostgreSQL Football League

This is my personal project for learning PostgreSQL through the design, implementation, operation, and analysis of a fictional football-league database.

The project is database-first: PostgreSQL, SQL migrations, generated data, query design, performance analysis, and operational workflows are the primary deliverables. It also includes a LangGraph-powered natural-language analyst that safely answers questions using the real PostgreSQL data.

## Project overview

The system models a fictional football league across many seasons. A Python generator creates teams, players, fixtures, lineups, substitutions, cards, player-match statistics, and goals.

PostgreSQL stores the data, enforces integrity rules, exposes analytical views, and supports performance and operations exercises.

The generated performance dataset currently contains approximately:

```text
100 seasons
4 teams
80 players
1,200 matches
43,200 lineup selections
30,000 player-match-stat records
4,800 goal events
```

## Natural-language database analyst

This repository includes a safe natural-language analyst for the football database, built with LangGraph, OpenAI, PostgreSQL, SQLGlot, and Streamlit.

Users can ask football questions in plain English through either a command-line interface or a simple web app. The application:

- clarifies ambiguous questions before generating SQL;
- generates a proposed SQL query with an LLM;
- validates the query using a SQL parser;
- allows only safe read-only `SELECT` queries;
- uses a read-only PostgreSQL account and transaction;
- runs the approved query against the real database;
- gives the returned rows to the LLM for a grounded natural-language explanation;
- makes one controlled repair attempt if generated SQL fails validation or execution.

The LLM never receives direct control of PostgreSQL. LangGraph coordinates the workflow, routing decisions, clarification path, retry loop, and final response.

Run the web app locally:

```bash
source analyst/.venv/bin/activate
streamlit run analyst/web_app.py
```

For the full analyst architecture, safety design, setup instructions, and test commands, see [the analyst documentation](analyst/README.md).

## Technology stack

- PostgreSQL 17
- Docker Compose / Docker Desktop
- Python 3
- `psycopg` for PostgreSQL connectivity
- `Faker` for synthetic data generation
- LangGraph for workflow orchestration and conditional routing
- OpenAI for structured question assessment, SQL generation, repair, and result explanations
- SQLGlot for parser-based SQL validation
- Streamlit for the analyst web interface
- SQL migrations, views, materialized views, functions, triggers, and indexes

## Data model

Core entities:

```text
seasons
teams
players
matches
goals
lineups
cards
substitutions
player_match_stats
```

Key relationships:

```text
seasons ──< matches >── teams
teams ──< players
matches ──< goals >── players
matches ──< lineups >── players
matches ──< cards >── players
matches ──< substitutions
matches ──< player_match_stats >── players
```

## Local setup

Requirements:

- Docker Desktop
- Python 3.10+

Start PostgreSQL:

```bash
docker compose up -d
```

Connect with `psql`:

```bash
docker compose exec db psql -U postgres -d football_league
```

Create and activate the database-project Python environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install "psycopg[binary]" Faker
```

Run the data generator:

```bash
python scripts/generate_data.py
```

Refresh the cached standings after regenerating match data:

```sql
REFRESH MATERIALIZED VIEW season_standings;
```

## Migrations

The schema is managed through ordered SQL migrations in `migrations/`.

```text
001_initial_schema.sql
002_create_lineups.sql
003_create_cards.sql
004_create_substitutions.sql
005_create_player_match_stats.sql
006_create_player_rolling_form_view.sql
007_create_season_standings_materialized_view.sql
008_create_player_season_average_rating_function.sql
009_create_cards_lineup_trigger.sql
010_add_player_match_stats_player_id_index.sql
011_add_goals_scorer_id_index.sql
012_create_readonly_role.sql
013_create_football_analyst_role.sql
```

Apply a migration from the project root:

```bash
docker compose exec -T db psql -v ON_ERROR_STOP=1 -U postgres -d football_league < migrations/<migration_file>.sql
```

Applied migrations are treated as immutable. New schema changes are introduced through new numbered migration files.

## Learning phases

### Phase 0 — Project foundation

- Created a Docker-based PostgreSQL development environment.
- Defined project structure, naming conventions, and reset workflow.
- Documented setup and database commands.

### Phase 1 — Schema and basic SQL

- Created the initial relational schema for seasons, teams, players, matches, and goals.
- Used primary keys, foreign keys, PostgreSQL data types, `NOT NULL`, `UNIQUE`, `CHECK`, and default constraints.
- Applied the first schema migration and performed basic `INSERT` and `SELECT` operations.

### Phase 2 — Generated football data

- Created a Python generator using `psycopg` and `Faker`.
- Generated fictional teams, players, fixtures, results, and goal events.
- Used database transactions and verified that goal-event counts match recorded scorelines.

### Phase 3 — SQL querying and analysis

- Built reusable queries for top scorers, league standings, and readable match results.
- Practiced `JOIN`, `LEFT JOIN`, `WHERE`, `GROUP BY`, `HAVING`, `COUNT`, `AVG`, `CASE`, subqueries, CTEs, and sorting.
- Calculated league standings from raw match results rather than storing the table directly.

### Phase 4 — Rich match data

- Added lineups, card events, substitutions, and player-match statistics.
- Modeled a many-to-many match/player relationship through `lineups`.
- Generated starters, substitutes, player minutes, ratings, shots, and passing statistics.
- Validated data relationships with SQL.

### Phase 5 — Advanced analytics and automation

- Used window functions for rolling five-match player form, previous-match comparisons, and per-match ranking.
- Created the `player_rolling_form` view.
- Created the `season_standings` materialized view and refreshed it after data changes.
- Created a parameterized function for a player’s seasonal average rating.
- Created a trigger that rejects card events for players absent from the relevant lineup.

### Phase 6 — Performance, backups, and permissions

- Scaled the generator to 100 seasons for meaningful query-plan analysis.
- Used `EXPLAIN ANALYZE` to inspect sequential scans and bitmap index scans.
- Added indexes on `player_match_stats.player_id` and `goals.scorer_id`.
- Created a custom-format backup with `pg_dump` and restored it into a separate database with `pg_restore`.
- Created and tested a read-only PostgreSQL permission role.

### Phase 7 — LangGraph database analyst

- Built a LangGraph workflow that turns natural-language football questions into safe database answers.
- Added conditional routing for ambiguous questions, SQL validation, execution errors, and controlled repair attempts.
- Used structured LLM output for question assessment, SQL generation, SQL repair, and result explanations.
- Added SQLGlot parser-based validation and an allow-list of database tables.
- Created a restricted PostgreSQL analyst account with read-only permissions.
- Built a Streamlit web interface that includes the chat experience and an interactive workflow diagram.
- Added automated tests for SQL safety rules and LangGraph routing logic.

## Example queries

Run a saved query from the project root:

```bash
docker compose exec -T db psql -U postgres -d football_league < queries/04_player_rolling_form.sql
```

Inspect player form through the view:

```sql
SELECT *
FROM player_rolling_form
ORDER BY last_name, first_name, played_at;
```

Query the cached standings:

```sql
SELECT *
FROM season_standings
ORDER BY points DESC, goal_difference DESC, goals_for DESC;
```

## Performance example

Inspect the plan for a player-history query:

```sql
EXPLAIN ANALYZE
SELECT *
FROM player_match_stats
WHERE player_id = 1;
```

With the larger dataset and `idx_player_match_stats_player_id`, PostgreSQL uses an index-based plan rather than scanning every row.

## Backup and restore

Create a custom-format backup:

```bash
docker compose exec -T db pg_dump -U postgres -Fc football_league > backups/football_league.dump
```

Restore into a separate database:

```bash
docker compose exec db createdb -U postgres football_league_restore_test
docker compose exec -T db pg_restore -U postgres -d football_league_restore_test < backups/football_league.dump
```

## Repository structure

```text
.
├── analyst/       # LangGraph natural-language database analyst and Streamlit app
├── backups/       # Local database dumps; do not commit
├── exercises/     # SQL learning exercises
├── migrations/    # Ordered database schema changes
├── queries/       # Reusable analytical SQL queries
├── scripts/       # Python data generator
├── solutions/     # Exercise solutions
├── docker-compose.yml
└── README.md
```

## Development notes

- The Docker username/password are local development credentials only.
- Do not commit `.venv/`, `backups/`, `.env`, or `__pycache__/` to Git.
- The database generator deliberately resets fictional data on each run; it does not change the schema.
- Materialized views must be refreshed after data generation or other match-data changes.