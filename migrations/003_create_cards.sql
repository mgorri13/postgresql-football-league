CREATE TABLE cards (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  match_id BIGINT NOT NULL REFERENCES matches(id),
  player_id BIGINT NOT NULL REFERENCES players(id),
  minute SMALLINT NOT NULL CHECK (minute BETWEEN 1 AND 130),
  card_type TEXT NOT NULL CHECK (
    card_type IN ('yellow', 'red')
  ),
  UNIQUE (match_id, player_id, minute, card_type)
);