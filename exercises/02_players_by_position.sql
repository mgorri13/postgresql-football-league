SELECT
  teams.name,
  players.position,
  COUNT(players.id) AS player_amount
FROM players
JOIN teams ON teams.id = players.team_id
GROUP BY teams.name, players.position
ORDER BY teams.name, players.position;