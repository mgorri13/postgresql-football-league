WITH team_results AS (
  SELECT
    season_id,
    home_team_id AS team_id,
    home_score AS goals_for,
    away_score AS goals_against,
    CASE
      WHEN home_score > away_score THEN 3
      WHEN home_score = away_score THEN 1
      ELSE 0
    END AS points
  FROM matches

  UNION ALL

  SELECT
    season_id,
    away_team_id AS team_id,
    away_score AS goals_for,
    home_score AS goals_against,
    CASE
      WHEN away_score > home_score THEN 3
      WHEN away_score = home_score THEN 1
      ELSE 0
    END AS points
  FROM matches
),

standings AS (
  SELECT
    season_id,
    team_id,
    COUNT(*) AS matches_played,
    SUM(CASE WHEN points = 3 THEN 1 ELSE 0 END) AS wins,
    SUM(CASE WHEN points = 1 THEN 1 ELSE 0 END) AS draws,
    SUM(CASE WHEN points = 0 THEN 1 ELSE 0 END) AS losses,
    SUM(goals_for) AS goals_for,
    SUM(goals_against) AS goals_against,
    SUM(goals_for - goals_against) AS goal_difference,
    SUM(points) AS points
  FROM team_results
  GROUP BY season_id, team_id
)

SELECT
  teams.name AS team,
  standings.matches_played,
  standings.wins,
  standings.draws,
  standings.losses,
  standings.goals_for,
  standings.goals_against,
  standings.goal_difference,
  standings.points
FROM standings
JOIN teams ON teams.id = standings.team_id
ORDER BY
  standings.points DESC,
  standings.goal_difference DESC,
  standings.goals_for DESC,
  teams.name;