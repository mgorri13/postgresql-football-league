# PostgreSQL Football League

This is my personal project for learning PostgreSQL through the design, implementation, operation, and analysis of a fictional football-league database. It is intentionally database-first: the deliverables are the PostgreSQL schema, migrations, data generator, analytical SQL, performance work, and operational workflows rather than a user interface.

## Overview

The project models seasons, teams, players, fixtures, goals, lineups, cards, substitutions, and player-match statistics. A Python generator creates synthetic but internally consistent data; PostgreSQL stores it, enforces integrity rules, and exposes analytical and operational capabilities.

The performance dataset contains approximately 100 seasons, 1,200 matches, 43,200 lineup selections, 30,000 player-match-stat rows, and 4,800 goal events.

## Stack

- PostgreSQL 17
- Docker Compose / Docker Desktop
- Python 3
- `psycopg` and `Faker`
- SQL migrations, analytical queries, views, materialized views, functions, triggers, indexes, and role-based permissions

## Data model

```text
seasons ──< matches >── teams
teams ──< players
matches ──< goals >── players
matches ──< lineups >── players
matches ──< cards >── players
matches ──< substitutions
matches ──< player_match_stats >── players
```

## Setup

Requirements: Docker Desktop and Python 3.10+.

```bash
docker compose up -d

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Connect to PostgreSQL:

```bash
docker compose exec db psql -U postgres -d football_league
```

Run the generator:

```bash
python scripts/generate_data.py
```

After regenerating match data, refresh the cached standings:

```sql
REFRESH MATERIALIZED VIEW season_standings;
```

## Migrations

The database schema is versioned through ordered migrations in `migrations/`.

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
```

Apply one migration from the project root:

```bash
docker compose exec -T db psql -v ON_ERROR_STOP=1 -U postgres -d football_league < migrations/<migration_file>.sql
```

Applied migrations are immutable; subsequent schema changes require a new numbered migration.

## Learning phases

### Phase 0 — Foundation

Created a Docker-based PostgreSQL environment, project structure, setup documentation, conventions, and reset workflow.

### Phase 1 — Schema and basic SQL

Created the initial relational model for seasons, teams, players, matches, and goals. Used primary and foreign keys, PostgreSQL types, identity columns, and `NOT NULL`, `UNIQUE`, `CHECK`, and default constraints.

### Phase 2 — Generated data

Built a Python generator using `psycopg` and `Faker`. It creates seasons, teams, players, home-and-away fixtures, results, and matching goal events in transactions.

### Phase 3 — Querying and analysis

Built analytical queries with `JOIN`, `LEFT JOIN`, `WHERE`, `GROUP BY`, `HAVING`, aggregates, `CASE`, subqueries, and CTEs. Queries include top scorers, readable match results, and a league table calculated from raw results.

### Phase 4 — Rich match data

Added lineups, cards, substitutions, and player-match statistics. The generator creates starters, benches, substitutions, minutes played, ratings, shots, and passing statistics.

### Phase 5 — Advanced analytics and automation

Used window functions for rolling five-match form, previous-match comparisons, and per-match rankings. Added the `player_rolling_form` view, the `season_standings` materialized view, a parameterized average-rating function, and a trigger that rejects cards for players absent from a match lineup.

### Phase 6 — Performance, backups, and permissions

Scaled the generator to 100 seasons. Used `EXPLAIN ANALYZE` to compare sequential and bitmap index scans, indexed player statistics and goal scorers, created/restored a `pg_dump` backup, and created a read-only PostgreSQL role.

## Example analytics

Run a saved query:

```bash
docker compose exec -T db psql -U postgres -d football_league < queries/04_player_rolling_form.sql
```

Query rolling player form:

```sql
SELECT *
FROM player_rolling_form
ORDER BY last_name, first_name, played_at;
```

Query cached standings:

```sql
SELECT *
FROM season_standings
ORDER BY points DESC, goal_difference DESC, goals_for DESC;
```

Inspect an execution plan:

```sql
EXPLAIN ANALYZE
SELECT *
FROM player_match_stats
WHERE player_id = 1;
```

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
backups/       # Local dumps; excluded from Git
exercises/     # SQL exercises
migrations/    # Ordered schema changes
queries/       # Reusable analytical SQL
scripts/       # Python data generator
solutions/     # Exercise solutions
```

## Development notes

- Docker credentials are local development credentials only.
- The generator resets fictional data; it does not change the schema.
- Do not commit `.venv/`, backups, environment files, or Python cache files.
- Materialized views require explicit refresh after source-data changes.
