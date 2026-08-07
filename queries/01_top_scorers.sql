SELECT
  players.first_name,
  players.last_name,
  teams.name AS team_name,
  COUNT(goals.id) AS goals_scored
FROM goals
JOIN players ON players.id = goals.scorer_id
JOIN teams ON teams.id = players.team_id
GROUP BY
  players.id,
  players.first_name,
  players.last_name,
  teams.name
ORDER BY goals_scored DESC, players.last_name;