# PostgreSQL Learning Project: Fictional Football League

## Purpose

Build a fictional football-league database whose sole purpose is to teach you PostgreSQL. This is not initially a web application and it does not require you to enter real data manually.

You will create the database, generate realistic-enough fake data, and use SQL to answer increasingly difficult questions about it.

## Project idea

Model one or more fictional football leagues across multiple seasons.

The database will contain teams, players, fixtures, match results, and match events such as goals and cards. Later versions can add lineups, transfers, contracts, injuries, and detailed player statistics.

Example questions your database should answer:

- Who are the top scorers in a season?
- What is the current league table, calculated from match results?
- Which team has the best home record?
- Which players have scored in three consecutive matches?
- Who has the highest rolling five-match rating?
- Which teams improved most between two seasons?

## Why this is a good PostgreSQL project

Football data is naturally relational and time-based:

- A team has many players.
- A player can appear in many matches.
- A match has many events.
- A season has many fixtures and a calculated standings table.
- Rules such as valid scorelines, unique fixtures, and non-overlapping contracts can be enforced in the database.

This lets you learn basic SQL first, then progressively use PostgreSQL features such as constraints, indexes, views, functions, triggers, window functions, transactions, range types, full-text search, partitioning, and query planning.

## Start small

Build only this first:

```text
seasons
teams
players
matches
goals
```

For the first version, generate a league with four teams, roughly 20 players per team, and one home-and-away season.

Suggested initial tables:

```text
seasons
  id, name, starts_on, ends_on

teams
  id, name, city, founded_year

players
  id, team_id, first_name, last_name, position, date_of_birth

matches
  id, season_id, home_team_id, away_team_id, played_at,
  home_score, away_score

goals
  id, match_id, scorer_id, minute, is_own_goal
```

## How the database gets populated

Write a small data-generator script instead of entering data by hand. Python is a good choice because it is easy to read and has useful libraries:

- `psycopg`: connects Python to PostgreSQL.
- `Faker`: generates fictional names, cities, and dates.
- Python's built-in `random`: creates scores and match events.

The script should:

1. Create a season.
2. Generate teams and players.
3. Generate a valid fixture list so every team plays each other home and away.
4. Generate plausible match scores.
5. Create a goal event for each goal in the result.
6. Insert data in dependency order, preferably inside transactions.

The simulation does not need to be perfect. It only needs to create varied, consistent data. Improve realism later by assigning team strength and favouring attackers as scorers.

## Learning path

### Milestone 1 — Schema and basic SQL

Learn:

- `CREATE TABLE`, primary keys, foreign keys, and data types
- `INSERT`, `SELECT`, `UPDATE`, and `DELETE`
- `NOT NULL`, `CHECK`, and `UNIQUE` constraints
- basic filtering, sorting, and joins

Deliverable: a small generated season and queries for teams, players, fixtures, and scorers.

### Milestone 2 — League statistics

Learn:

- `GROUP BY`, `HAVING`, aggregate functions, subqueries, and CTEs
- calculating standings from matches instead of storing them
- `CASE` expressions

Deliverable: top-scorer, team-form, and league-table queries.

### Milestone 3 — Rich match data

Add:

```text
lineups
match_events
player_match_stats
cards
substitutions
```

Learn:

- many-to-many relationships
- enums or lookup tables for positions and event types
- transactions for recording a whole match safely
- JSONB for optional event details, such as shot location

### Milestone 4 — Advanced analytics

Learn:

- window functions: `RANK`, `LAG`, `LEAD`, and rolling averages
- views and materialized views
- functions and triggers

Deliverable: leaderboards, recent-form tables, scoring streaks, and a materialized league table.

### Milestone 5 — Database performance and operations

Generate ten or more seasons with a large number of match events.

Learn:

- indexes and `EXPLAIN ANALYZE`
- index selection and query tuning
- partitioning event tables by season
- backup and restore with `pg_dump` and `pg_restore`
- roles and permissions

### Milestone 6 — Advanced data integrity

Add contracts, transfers, and injuries.

Learn:

- PostgreSQL date ranges
- exclusion constraints
- preventing overlapping player contracts
- triggers for automatic timestamping or validation

## Suggested repository structure

```text
postgres-football-league/
  README.md
  docker-compose.yml
  migrations/
  seeds/
  scripts/
    generate_data.py
  queries/
  exercises/
  solutions/
```

Keep each learning exercise as a separate SQL file. Write the query yourself first, then compare it against your solution later.

## Ground rule

Do not build a UI first. The database is the project.

Only add a small API or interface after you can comfortably model data, generate it, query it, enforce integrity, and analyze performance in PostgreSQL.
