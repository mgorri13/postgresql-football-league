SELECT
  matches.played_at,
  home_team.name AS home_team_name,
  matches.home_score,
  matches.away_score,
  away_team.name AS away_team_name,
  matches.home_score + matches.away_score AS total_goals
FROM matches
JOIN teams AS home_team ON home_team.id = matches.home_team_id
JOIN teams AS away_team ON away_team.id = matches.away_team_id
WHERE matches.home_score + matches.away_score > (
  SELECT AVG(home_score + away_score)
  FROM matches
)
ORDER BY matches.played_at;