SELECT
  players.first_name,
  players.last_name,
  teams.name,
  COUNT(goals.id) AS goals_scored

FROM goals
JOIN players ON goals.scorer_id=players.id
JOIN teams ON teams.id=players.team_id

GROUP BY players.id, players.first_name, players.last_name, teams.name
HAVING COUNT(goals.id) >=2
ORDER BY goals_scored DESC;

