CREATE FUNCTION ensure_carded_player_is_in_lineup()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM lineups
    WHERE lineups.match_id = NEW.match_id
      AND lineups.player_id = NEW.player_id
  ) THEN
    RAISE EXCEPTION
      'Player % is not in the lineup for match %',
      NEW.player_id,
      NEW.match_id;
  END IF;

  RETURN NEW;
END;
$$;

CREATE TRIGGER cards_require_lineup
BEFORE INSERT OR UPDATE OF match_id, player_id
ON cards
FOR EACH ROW
EXECUTE FUNCTION ensure_carded_player_is_in_lineup();