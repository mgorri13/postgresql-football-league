SELECT
  players.first_name,
  players.last_name,
  COUNT(goals.id) AS goal_count,
  teams.name AS team_name
FROM players
JOIN teams ON teams.id = players.team_id
LEFT JOIN goals ON goals.scorer_id = players.id
GROUP BY
  players.id,
  players.first_name,
  players.last_name,
  teams.name
ORDER BY goal_count DESC, players.last_name;