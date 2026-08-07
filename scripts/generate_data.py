from datetime import date, datetime, timedelta, timezone
from itertools import combinations
import random

from faker import Faker
import psycopg

DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/football_league"
SEASON_COUNT = 100

fake = Faker()


def reset_database(cursor):
    cursor.execute("""
        TRUNCATE TABLE player_match_stats, substitutions, cards, lineups,
        goals, matches, players, teams, seasons
        RESTART IDENTITY;
    """)


def create_seasons(cursor):
    season_ids = []

    for season_number in range(SEASON_COUNT):
        start_year = 2025 + season_number

        cursor.execute(
            """
            INSERT INTO seasons (name, starts_on, ends_on)
            VALUES (%s, %s, %s)
            RETURNING id;
            """,
            (
                f"{start_year}-{start_year + 1}",
                date(start_year, 8, 1),
                date(start_year + 1, 5, 31),
            ),
        )

        season_ids.append(cursor.fetchone()[0])

    return season_ids


def create_teams(cursor):
    team_names = [
        "Northbridge FC",
        "River City United",
        "Eastwood Rovers",
        "Lakeside Athletic",
    ]

    team_ids = []

    for name in team_names:
        cursor.execute(
            """
            INSERT INTO teams (name, city, founded_year)
            VALUES (%s, %s, %s)
            RETURNING id;
            """,
            (name, fake.city(), fake.random_int(min=1890, max=2015)),
        )
        team_ids.append(cursor.fetchone()[0])

    return team_ids


def create_players(cursor, team_ids):
    position_template = (
        ["goalkeeper"] * 2
        + ["defender"] * 7
        + ["midfielder"] * 7
        + ["forward"] * 4
    )

    players = []

    for team_id in team_ids:
        positions = position_template.copy()
        random.shuffle(positions)

        for position in positions:
            players.append(
                (
                    team_id,
                    fake.first_name(),
                    fake.last_name(),
                    position,
                    fake.date_of_birth(minimum_age=18, maximum_age=36),
                )
            )

    cursor.executemany(
        """
        INSERT INTO players (
            team_id, first_name, last_name, position, date_of_birth
        )
        VALUES (%s, %s, %s, %s, %s);
        """,
        players,
    )


def create_matches(cursor, season_ids, team_ids):
    team_pairs = list(combinations(team_ids, 2))

    fixtures = team_pairs + [
        (away_team_id, home_team_id)
        for home_team_id, away_team_id in team_pairs
    ]

    matches = []

    for season_number, season_id in enumerate(season_ids):
        first_kickoff = datetime(
            2025 + season_number,
            8,
            9,
            15,
            0,
            tzinfo=timezone.utc,
        )

        for match_number, (home_team_id, away_team_id) in enumerate(fixtures):
            matches.append(
                (
                    season_id,
                    home_team_id,
                    away_team_id,
                    first_kickoff + timedelta(days=match_number * 7),
                    random.randint(0, 4),
                    random.randint(0, 4),
                )
            )

    cursor.executemany(
        """
        INSERT INTO matches (
            season_id, home_team_id, away_team_id,
            played_at, home_score, away_score
        )
        VALUES (%s, %s, %s, %s, %s, %s);
        """,
        matches,
    )


def create_lineups(cursor):
    cursor.execute("""
        SELECT id, home_team_id, away_team_id
        FROM matches
        ORDER BY id;
    """)
    matches = cursor.fetchall()

    cursor.execute("""
        SELECT id, team_id, position
        FROM players;
    """)

    players_by_team = {}

    for player_id, team_id, position in cursor.fetchall():
        players_by_team.setdefault(team_id, []).append(
            (player_id, position)
        )

    lineups = []

    for match_id, home_team_id, away_team_id in matches:
        for team_id in (home_team_id, away_team_id):
            team_players = players_by_team[team_id]

            goalkeepers = [
                player for player in team_players
                if player[1] == "goalkeeper"
            ]
            defenders = [
                player for player in team_players
                if player[1] == "defender"
            ]
            midfielders = [
                player for player in team_players
                if player[1] == "midfielder"
            ]
            forwards = [
                player for player in team_players
                if player[1] == "forward"
            ]

            starters = (
                random.sample(goalkeepers, 1)
                + random.sample(defenders, 4)
                + random.sample(midfielders, 3)
                + random.sample(forwards, 3)
            )

            starter_ids = {player_id for player_id, _ in starters}

            substitute_candidates = [
                player for player in team_players
                if player[0] not in starter_ids
            ]
            substitutes = random.sample(substitute_candidates, 7)

            for player_id, position in starters:
                lineups.append((match_id, player_id, True, position))

            for player_id, position in substitutes:
                lineups.append((match_id, player_id, False, position))

    cursor.executemany(
        """
        INSERT INTO lineups (
            match_id, player_id, is_starter, position
        )
        VALUES (%s, %s, %s, %s);
        """,
        lineups,
    )


def create_cards(cursor):
    cursor.execute("SELECT id FROM matches ORDER BY id;")
    matches = cursor.fetchall()

    cursor.execute("""
        SELECT match_id, player_id
        FROM lineups;
    """)

    players_by_match = {}

    for match_id, player_id in cursor.fetchall():
        players_by_match.setdefault(match_id, []).append(player_id)

    cards = []

    for (match_id,) in matches:
        card_count = random.choices(
            [0, 1, 2, 3],
            weights=[45, 35, 15, 5],
            k=1,
        )[0]

        carded_players = random.sample(
            players_by_match[match_id],
            card_count,
        )
        card_minutes = sorted(
            random.sample(range(1, 91), card_count)
        )

        for player_id, minute in zip(carded_players, card_minutes):
            card_type = random.choices(
                ["yellow", "red"],
                weights=[9, 1],
                k=1,
            )[0]

            cards.append((match_id, player_id, minute, card_type))

    if cards:
        cursor.executemany(
            """
            INSERT INTO cards (
                match_id, player_id, minute, card_type
            )
            VALUES (%s, %s, %s, %s);
            """,
            cards,
        )


def create_substitutions(cursor):
    cursor.execute("""
        SELECT
            lineups.match_id,
            players.team_id,
            lineups.player_id,
            lineups.is_starter
        FROM lineups
        JOIN players ON players.id = lineups.player_id;
    """)

    squads = {}

    for match_id, team_id, player_id, is_starter in cursor.fetchall():
        squads.setdefault(
            (match_id, team_id),
            {"starters": [], "substitutes": []},
        )

        if is_starter:
            squads[(match_id, team_id)]["starters"].append(player_id)
        else:
            squads[(match_id, team_id)]["substitutes"].append(player_id)

    substitutions = []

    for (match_id, team_id), squad in squads.items():
        substitution_count = random.randint(1, 3)

        players_out = random.sample(
            squad["starters"],
            substitution_count,
        )
        players_in = random.sample(
            squad["substitutes"],
            substitution_count,
        )
        minutes = sorted(
            random.sample(range(46, 91), substitution_count)
        )

        for player_out_id, player_in_id, minute in zip(
            players_out,
            players_in,
            minutes,
        ):
            substitutions.append(
                (match_id, player_out_id, player_in_id, minute)
            )

    cursor.executemany(
        """
        INSERT INTO substitutions (
            match_id, player_out_id, player_in_id, minute
        )
        VALUES (%s, %s, %s, %s);
        """,
        substitutions,
    )


def create_player_match_stats(cursor):
    cursor.execute("""
        SELECT match_id, player_id, is_starter
        FROM lineups;
    """)

    starters_by_match = {}

    for match_id, player_id, is_starter in cursor.fetchall():
        if is_starter:
            starters_by_match.setdefault(match_id, []).append(player_id)

    cursor.execute("""
        SELECT match_id, player_out_id, player_in_id, minute
        FROM substitutions;
    """)

    substitutions_by_match = {}

    for match_id, player_out_id, player_in_id, minute in cursor.fetchall():
        substitutions_by_match.setdefault(match_id, []).append(
            (player_out_id, player_in_id, minute)
        )

    stats = []

    for match_id, starters in starters_by_match.items():
        substitutions = substitutions_by_match.get(match_id, [])

        outgoing_minutes = {
            player_out_id: minute
            for player_out_id, _, minute in substitutions
        }

        for player_id in starters:
            minutes_played = outgoing_minutes.get(player_id, 90)

            passes_attempted = random.randint(
                max(1, minutes_played // 3),
                max(2, minutes_played),
            )
            passes_completed = random.randint(
                int(passes_attempted * 0.6),
                passes_attempted,
            )

            stats.append(
                (
                    match_id,
                    player_id,
                    minutes_played,
                    round(random.uniform(5.0, 9.5), 1),
                    random.randint(0, max(1, minutes_played // 18)),
                    passes_completed,
                    passes_attempted,
                )
            )

        for _, player_in_id, minute in substitutions:
            minutes_played = max(1, 91 - minute)

            passes_attempted = random.randint(
                max(1, minutes_played // 3),
                max(2, minutes_played),
            )
            passes_completed = random.randint(
                int(passes_attempted * 0.6),
                passes_attempted,
            )

            stats.append(
                (
                    match_id,
                    player_in_id,
                    minutes_played,
                    round(random.uniform(5.0, 9.5), 1),
                    random.randint(0, max(1, minutes_played // 18)),
                    passes_completed,
                    passes_attempted,
                )
            )

    cursor.executemany(
        """
        INSERT INTO player_match_stats (
            match_id,
            player_id,
            minutes_played,
            rating,
            shots,
            passes_completed,
            passes_attempted
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s);
        """,
        stats,
    )


def create_goals(cursor):
    cursor.execute("""
        SELECT id, home_team_id, away_team_id, home_score, away_score
        FROM matches
        ORDER BY id;
    """)
    matches = cursor.fetchall()

    cursor.execute("""
        SELECT
            player_match_stats.match_id,
            player_match_stats.player_id,
            players.team_id
        FROM player_match_stats
        JOIN players ON players.id = player_match_stats.player_id;
    """)

    players_by_match_and_team = {}

    for match_id, player_id, team_id in cursor.fetchall():
        players_by_match_and_team.setdefault(
            (match_id, team_id),
            [],
        ).append(player_id)

    goals = []

    for match_id, home_team_id, away_team_id, home_score, away_score in matches:
        scoring_teams = (
            [home_team_id] * home_score
            + [away_team_id] * away_score
        )

        random.shuffle(scoring_teams)

        goal_minutes = sorted(
            random.sample(range(1, 91), len(scoring_teams))
        )

        for scoring_team_id, minute in zip(scoring_teams, goal_minutes):
            scorer_id = random.choice(
                players_by_match_and_team[(match_id, scoring_team_id)]
            )

            goals.append((match_id, scorer_id, minute, False))

    if goals:
        cursor.executemany(
            """
            INSERT INTO goals (
                match_id, scorer_id, minute, is_own_goal
            )
            VALUES (%s, %s, %s, %s);
            """,
            goals,
        )


def main():
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            reset_database(cursor)

            season_ids = create_seasons(cursor)
            team_ids = create_teams(cursor)
            create_players(cursor, team_ids)
            create_matches(cursor, season_ids, team_ids)
            create_lineups(cursor)
            create_cards(cursor)
            create_substitutions(cursor)
            create_player_match_stats(cursor)
            create_goals(cursor)

            cursor.execute("SELECT COUNT(*) FROM teams;")
            team_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM players;")
            player_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM matches;")
            match_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM lineups;")
            lineup_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM cards;")
            card_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM substitutions;")
            substitution_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM player_match_stats;")
            stats_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM goals;")
            goal_count = cursor.fetchone()[0]

    print(f"Created seasons: {len(season_ids)}")
    print(f"Created teams: {team_count}")
    print(f"Created players: {player_count}")
    print(f"Created matches: {match_count}")
    print(f"Created lineup selections: {lineup_count}")
    print(f"Created cards: {card_count}")
    print(f"Created substitutions: {substitution_count}")
    print(f"Created player match stats: {stats_count}")
    print(f"Created goals: {goal_count}")


if __name__ == "__main__":
    main()