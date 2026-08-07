SELECT
  players.first_name,
  players.last_name,
  teams.name AS team_name,
  matches.played_at,
  player_match_stats.rating,
  ROUND(
    AVG(player_match_stats.rating) OVER (
      PARTITION BY player_match_stats.player_id
      ORDER BY matches.played_at
      ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
    ),
    2
  ) AS rolling_five_match_rating
FROM player_match_stats
JOIN players ON players.id = player_match_stats.player_id
JOIN teams ON teams.id = players.team_id
JOIN matches ON matches.id = player_match_stats.match_id
ORDER BY
  players.last_name,
  players.first_name,
  matches.played_at;