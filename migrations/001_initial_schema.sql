CREATE TABLE seasons (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  starts_on DATE NOT NULL,
  ends_on DATE NOT NULL,
  CHECK (ends_on > starts_on)
);

CREATE TABLE teams (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  city TEXT NOT NULL,
  founded_year SMALLINT NOT NULL CHECK (founded_year >= 1800)
);

CREATE TABLE players (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  team_id BIGINT NOT NULL REFERENCES teams(id),
  first_name TEXT NOT NULL,
  last_name TEXT NOT NULL,
  position TEXT NOT NULL CHECK (
    position IN ('goalkeeper', 'defender', 'midfielder', 'forward')
  ),
  date_of_birth DATE NOT NULL
);

CREATE TABLE matches (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  season_id BIGINT NOT NULL REFERENCES seasons(id),
  home_team_id BIGINT NOT NULL REFERENCES teams(id),
  away_team_id BIGINT NOT NULL REFERENCES teams(id),
  played_at TIMESTAMPTZ NOT NULL,
  home_score SMALLINT NOT NULL CHECK (home_score >= 0),
  away_score SMALLINT NOT NULL CHECK (away_score >= 0),
  CHECK (home_team_id <> away_team_id),
  UNIQUE (season_id, home_team_id, away_team_id)
);

CREATE TABLE goals (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  match_id BIGINT NOT NULL REFERENCES matches(id),
  scorer_id BIGINT NOT NULL REFERENCES players(id),
  minute SMALLINT NOT NULL CHECK (minute BETWEEN 1 AND 130),
  is_own_goal BOOLEAN NOT NULL DEFAULT FALSE
);