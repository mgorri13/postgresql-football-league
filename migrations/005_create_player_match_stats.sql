CREATE TABLE player_match_stats (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  match_id BIGINT NOT NULL REFERENCES matches(id),
  player_id BIGINT NOT NULL REFERENCES players(id),
  minutes_played SMALLINT NOT NULL CHECK (
    minutes_played BETWEEN 1 AND 130
  ),
  rating NUMERIC(3, 1) NOT NULL CHECK (
    rating BETWEEN 0 AND 10
  ),
  shots SMALLINT NOT NULL DEFAULT 0 CHECK (shots >= 0),
  passes_completed SMALLINT NOT NULL DEFAULT 0 CHECK (
    passes_completed >= 0
  ),
  passes_attempted SMALLINT NOT NULL DEFAULT 0 CHECK (
    passes_attempted >= passes_completed
  ),
  UNIQUE (match_id, player_id)
);