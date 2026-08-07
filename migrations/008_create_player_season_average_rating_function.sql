CREATE FUNCTION player_season_average_rating(
  target_player_id BIGINT,
  target_season_id BIGINT
)
RETURNS NUMERIC(4, 2)
LANGUAGE sql
STABLE
AS $$
  SELECT ROUND(AVG(player_match_stats.rating), 2)
  FROM player_match_stats
  JOIN matches ON matches.id = player_match_stats.match_id
  WHERE player_match_stats.player_id = target_player_id
    AND matches.season_id = target_season_id;
$$;