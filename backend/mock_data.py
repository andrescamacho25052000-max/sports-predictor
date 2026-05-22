TEAMS = {
    "Barcelona": {
        "wins_last5": 4, "draws_last5": 1, "losses_last5": 0,
        "goals_scored_last5": 12, "goals_conceded_last5": 3,
        "possession_avg": 62, "shots_on_target_avg": 7.2,
        "injured_players": 1, "ranking": 2,
        "yellow_cards_last5": 3, "red_cards_last5": 0,
    },
    "Real Madrid": {
        "wins_last5": 3, "draws_last5": 1, "losses_last5": 1,
        "goals_scored_last5": 9, "goals_conceded_last5": 5,
        "possession_avg": 55, "shots_on_target_avg": 6.1,
        "injured_players": 2, "ranking": 3,
        "yellow_cards_last5": 4, "red_cards_last5": 0,
    },
    "Arsenal": {
        "wins_last5": 4, "draws_last5": 0, "losses_last5": 1,
        "goals_scored_last5": 10, "goals_conceded_last5": 4,
        "possession_avg": 58, "shots_on_target_avg": 6.8,
        "injured_players": 2, "ranking": 4,
        "yellow_cards_last5": 5, "red_cards_last5": 0,
    },
    "Chelsea": {
        "wins_last5": 2, "draws_last5": 2, "losses_last5": 1,
        "goals_scored_last5": 7, "goals_conceded_last5": 6,
        "possession_avg": 52, "shots_on_target_avg": 5.5,
        "injured_players": 3, "ranking": 6,
        "yellow_cards_last5": 6, "red_cards_last5": 1,
    },
    "Manchester City": {
        "wins_last5": 5, "draws_last5": 0, "losses_last5": 0,
        "goals_scored_last5": 14, "goals_conceded_last5": 2,
        "possession_avg": 65, "shots_on_target_avg": 8.0,
        "injured_players": 0, "ranking": 1,
        "yellow_cards_last5": 2, "red_cards_last5": 0,
    },
    "Liverpool": {
        "wins_last5": 3, "draws_last5": 2, "losses_last5": 0,
        "goals_scored_last5": 11, "goals_conceded_last5": 4,
        "possession_avg": 57, "shots_on_target_avg": 6.5,
        "injured_players": 1, "ranking": 5,
        "yellow_cards_last5": 3, "red_cards_last5": 0,
    },
    "Atletico Madrid": {
        "wins_last5": 3, "draws_last5": 2, "losses_last5": 0,
        "goals_scored_last5": 7, "goals_conceded_last5": 3,
        "possession_avg": 48, "shots_on_target_avg": 5.0,
        "injured_players": 2, "ranking": 4,
        "yellow_cards_last5": 7, "red_cards_last5": 1,
    },
    "PSG": {
        "wins_last5": 4, "draws_last5": 0, "losses_last5": 1,
        "goals_scored_last5": 13, "goals_conceded_last5": 5,
        "possession_avg": 60, "shots_on_target_avg": 7.0,
        "injured_players": 1, "ranking": 3,
        "yellow_cards_last5": 4, "red_cards_last5": 0,
    },
    "Bayern Munich": {
        "wins_last5": 4, "draws_last5": 1, "losses_last5": 0,
        "goals_scored_last5": 15, "goals_conceded_last5": 4,
        "possession_avg": 63, "shots_on_target_avg": 7.8,
        "injured_players": 1, "ranking": 2,
        "yellow_cards_last5": 3, "red_cards_last5": 0,
    },
    "Borussia Dortmund": {
        "wins_last5": 2, "draws_last5": 1, "losses_last5": 2,
        "goals_scored_last5": 8, "goals_conceded_last5": 8,
        "possession_avg": 50, "shots_on_target_avg": 5.8,
        "injured_players": 3, "ranking": 7,
        "yellow_cards_last5": 5, "red_cards_last5": 0,
    },
}

LEAGUES = {
    "La Liga": {
        "matches": [
            {"home": "Barcelona", "away": "Real Madrid"},
            {"home": "Real Madrid", "away": "Atletico Madrid"},
            {"home": "Atletico Madrid", "away": "Barcelona"},
        ]
    },
    "Premier League": {
        "matches": [
            {"home": "Arsenal", "away": "Chelsea"},
            {"home": "Manchester City", "away": "Liverpool"},
            {"home": "Chelsea", "away": "Arsenal"},
            {"home": "Liverpool", "away": "Manchester City"},
        ]
    },
    "Ligue 1": {
        "matches": [
            {"home": "PSG", "away": "Lyon"},
        ]
    },
    "Bundesliga": {
        "matches": [
            {"home": "Bayern Munich", "away": "Borussia Dortmund"},
            {"home": "Borussia Dortmund", "away": "Bayern Munich"},
        ]
    },
    "Champions League": {
        "matches": [
            {"home": "Manchester City", "away": "Barcelona"},
            {"home": "Bayern Munich", "away": "Real Madrid"},
            {"home": "Arsenal", "away": "PSG"},
            {"home": "Liverpool", "away": "Atletico Madrid"},
        ]
    },
}

HEAD_TO_HEAD = {
    ("Barcelona", "Real Madrid"): {"barcelona_wins": 38, "real_madrid_wins": 32, "draws": 18},
    ("Arsenal", "Chelsea"): {"arsenal_wins": 30, "chelsea_wins": 22, "draws": 15},
    ("Manchester City", "Liverpool"): {"manchester_city_wins": 20, "liverpool_wins": 18, "draws": 12},
    ("Bayern Munich", "Borussia Dortmund"): {"bayern_munich_wins": 35, "borussia_dortmund_wins": 14, "draws": 20},
}
