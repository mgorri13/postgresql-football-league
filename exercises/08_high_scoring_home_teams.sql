SELECT
  teams.name AS team_name,
  AVG(matches.home_score) AS average_home_goals
FROM matches
JOIN teams ON teams.id = matches.home_team_id
GROUP BY
  teams.id,
  teams.name
HAVING AVG(matches.home_score) > 1
ORDER BY average_home_goals DESC;