CREATE TABLE substitutions (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  match_id BIGINT NOT NULL REFERENCES matches(id),
  player_out_id BIGINT NOT NULL REFERENCES players(id),
  player_in_id BIGINT NOT NULL REFERENCES players(id),
  minute SMALLINT NOT NULL CHECK (minute BETWEEN 1 AND 130),
  CHECK (player_out_id <> player_in_id),
  UNIQUE (match_id, player_out_id),
  UNIQUE (match_id, player_in_id)
);