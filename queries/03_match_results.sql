SELECT
  matches.played_at,
  home_team.name AS home_team,
  matches.home_score,
  matches.away_score,
  away_team.name AS away_team
FROM matches
JOIN teams AS home_team ON home_team.id = matches.home_team_id
JOIN teams AS away_team ON away_team.id = matches.away_team_id
ORDER BY matches.played_at;