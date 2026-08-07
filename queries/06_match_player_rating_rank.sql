SELECT
  matches.id AS match_id,
  matches.played_at,
  players.first_name,
  players.last_name,
  teams.name AS team_name,
  player_match_stats.rating,
  RANK() OVER (
    PARTITION BY player_match_stats.match_id
    ORDER BY player_match_stats.rating DESC
  ) AS rating_rank_in_match
FROM player_match_stats
JOIN players ON players.id = player_match_stats.player_id
JOIN teams ON teams.id = players.team_id
JOIN matches ON matches.id = player_match_stats.match_id
ORDER BY
  matches.played_at,
  rating_rank_in_match,
  players.last_name;