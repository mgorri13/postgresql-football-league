CREATE TABLE lineups (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  match_id BIGINT NOT NULL REFERENCES matches(id),
  player_id BIGINT NOT NULL REFERENCES players(id),
  is_starter BOOLEAN NOT NULL,
  position TEXT NOT NULL CHECK (
    position IN ('goalkeeper', 'defender', 'midfielder', 'forward')
  ),
  UNIQUE (match_id, player_id)
);