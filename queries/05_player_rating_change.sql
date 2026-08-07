SELECT
  players.first_name,
  players.last_name,
  teams.name AS team_name,
  matches.played_at,
  player_match_stats.rating AS current_rating,
  LAG(player_match_stats.rating) OVER (
    PARTITION BY player_match_stats.player_id
    ORDER BY matches.played_at
  ) AS previous_rating,
  player_match_stats.rating
    - LAG(player_match_stats.rating) OVER (
        PARTITION BY player_match_stats.player_id
        ORDER BY matches.played_at
      ) AS rating_change
FROM player_match_stats
JOIN players ON players.id = player_match_stats.player_id
JOIN teams ON teams.id = players.team_id
JOIN matches ON matches.id = player_match_stats.match_id
ORDER BY
  players.last_name,
  players.first_name,
  matches.played_at;