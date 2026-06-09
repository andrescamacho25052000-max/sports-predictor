"""
corners_cards_predictor.py
===========================
Predice mercados de córners y tarjetas usando distribución de Poisson,
igual que el modelo de goles, pero con datos de StatsBomb.
"""

import json
import math
from pathlib import Path
from functools import lru_cache

PROFILES_PATH = Path(__file__).parent / "ml" / "data" / "team_profiles_statsbomb.json"

# Promedios globales de fallback (calculados del dataset StatsBomb)
GLOBAL_CORNERS_PER_TEAM = 5.1
GLOBAL_YELLOW_PER_TEAM  = 1.9
GLOBAL_FOULS_PER_TEAM   = 12.5
GLOBAL_SHOTS_PER_TEAM   = 13.2

HOME_ADV_CORNERS = 1.05   # leve ventaja local en corners
HOME_ADV_CARDS   = 0.95   # local comete ligeramente menos faltas


@lru_cache(maxsize=1)
def _load_profiles() -> dict:
    if PROFILES_PATH.exists():
        with open(PROFILES_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _find_team(name: str, profiles: dict) -> dict | None:
    """Busca equipo por nombre exacto, luego parcial."""
    if name in profiles:
        return profiles[name]
    name_lower = name.lower()
    for k, v in profiles.items():
        if name_lower in k.lower() or k.lower() in name_lower:
            return v
    return None


def _poisson_prob(lam: float, k: int) -> float:
    """P(X = k) con distribución de Poisson."""
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def _over_under_probs(lam_home: float, lam_away: float) -> dict:
    """Probabilidades Over/Under para distintos umbrales."""
    lam_total = lam_home + lam_away
    result = {}
    for threshold in [6.5, 7.5, 8.5, 9.5, 10.5, 11.5]:
        # P(total > threshold) = 1 - P(total <= floor(threshold))
        k_max = int(threshold)
        prob_under = sum(_poisson_prob(lam_total, k) for k in range(k_max + 1))
        result[str(threshold)] = round(1 - prob_under, 4)
    return result


def _cards_over_under(lam_home: float, lam_away: float) -> dict:
    lam_total = lam_home + lam_away
    result = {}
    for threshold in [1.5, 2.5, 3.5, 4.5, 5.5]:
        k_max = int(threshold)
        prob_under = sum(_poisson_prob(lam_total, k) for k in range(k_max + 1))
        result[str(threshold)] = round(1 - prob_under, 4)
    return result


def predict_corners_cards(home_team: str, away_team: str) -> dict:
    """
    Predice mercados de córners y tarjetas para un partido.

    Retorna dict con:
      corners: { lambda_home, lambda_away, over_under, home_more, away_more, draw }
      yellow_cards: { lambda_home, lambda_away, over_under, home_more, away_more }
      fouls: { lambda_home, lambda_away }
      data_source: 'statsbomb' | 'global_average'
    """
    profiles = _load_profiles()

    home_profile = _find_team(home_team, profiles)
    away_profile = _find_team(away_team, profiles)

    data_source = "statsbomb" if (home_profile or away_profile) else "global_average"

    # Lambda corners
    home_corners_for  = (home_profile or {}).get("corners_for_avg",     GLOBAL_CORNERS_PER_TEAM)
    home_corners_ag   = (home_profile or {}).get("corners_against_avg",  GLOBAL_CORNERS_PER_TEAM)
    away_corners_for  = (away_profile or {}).get("corners_for_avg",     GLOBAL_CORNERS_PER_TEAM)
    away_corners_ag   = (away_profile or {}).get("corners_against_avg",  GLOBAL_CORNERS_PER_TEAM)

    lam_home_corners = ((home_corners_for + away_corners_ag) / 2) * HOME_ADV_CORNERS
    lam_away_corners = ((away_corners_for + home_corners_ag) / 2) / HOME_ADV_CORNERS
    lam_home_corners = round(max(lam_home_corners, 1.0), 2)
    lam_away_corners = round(max(lam_away_corners, 1.0), 2)

    # P(home > away), P(away > home), P(igual) en corners
    corner_probs = {"home_more": 0.0, "draw": 0.0, "away_more": 0.0}
    for h in range(25):
        ph = _poisson_prob(lam_home_corners, h)
        if ph < 1e-6:
            continue
        for a in range(25):
            pa = _poisson_prob(lam_away_corners, a)
            if pa < 1e-6:
                continue
            if h > a:
                corner_probs["home_more"] += ph * pa
            elif h < a:
                corner_probs["away_more"] += ph * pa
            else:
                corner_probs["draw"] += ph * pa

    corner_probs = {k: round(v, 4) for k, v in corner_probs.items()}

    # Lambda tarjetas amarillas
    home_yellow_for = (home_profile or {}).get("yellow_for_avg",     GLOBAL_YELLOW_PER_TEAM)
    home_yellow_ag  = (home_profile or {}).get("yellow_against_avg", GLOBAL_YELLOW_PER_TEAM)
    away_yellow_for = (away_profile or {}).get("yellow_for_avg",     GLOBAL_YELLOW_PER_TEAM)
    away_yellow_ag  = (away_profile or {}).get("yellow_against_avg", GLOBAL_YELLOW_PER_TEAM)

    lam_home_yellow = ((home_yellow_for + away_yellow_ag) / 2) * HOME_ADV_CARDS
    lam_away_yellow = ((away_yellow_for + home_yellow_ag) / 2) / HOME_ADV_CARDS
    lam_home_yellow = round(max(lam_home_yellow, 0.3), 2)
    lam_away_yellow = round(max(lam_away_yellow, 0.3), 2)

    # Lambda faltas
    home_fouls_for = (home_profile or {}).get("fouls_for_avg",     GLOBAL_FOULS_PER_TEAM)
    home_fouls_ag  = (home_profile or {}).get("fouls_against_avg", GLOBAL_FOULS_PER_TEAM)
    away_fouls_for = (away_profile or {}).get("fouls_for_avg",     GLOBAL_FOULS_PER_TEAM)
    away_fouls_ag  = (away_profile or {}).get("fouls_against_avg", GLOBAL_FOULS_PER_TEAM)

    lam_home_fouls = ((home_fouls_for + away_fouls_ag) / 2) * HOME_ADV_CARDS
    lam_away_fouls = ((away_fouls_for + home_fouls_ag) / 2) / HOME_ADV_CARDS
    lam_home_fouls = round(max(lam_home_fouls, 3.0), 2)
    lam_away_fouls = round(max(lam_away_fouls, 3.0), 2)

    # Over/Under tarjetas por equipo (0-N)
    home_yellow_dist = {
        str(k): round(_poisson_prob(lam_home_yellow, k), 4)
        for k in range(6)
    }
    away_yellow_dist = {
        str(k): round(_poisson_prob(lam_away_yellow, k), 4)
        for k in range(6)
    }

    return {
        "data_source": data_source,
        "corners": {
            "lambda_home":  lam_home_corners,
            "lambda_away":  lam_away_corners,
            "expected_home": lam_home_corners,
            "expected_away": lam_away_corners,
            "expected_total": round(lam_home_corners + lam_away_corners, 2),
            "over_under": _over_under_probs(lam_home_corners, lam_away_corners),
            "home_more":  corner_probs["home_more"],
            "away_more":  corner_probs["away_more"],
            "equal":      corner_probs["draw"],
        },
        "yellow_cards": {
            "lambda_home":    lam_home_yellow,
            "lambda_away":    lam_away_yellow,
            "expected_home":  lam_home_yellow,
            "expected_away":  lam_away_yellow,
            "expected_total": round(lam_home_yellow + lam_away_yellow, 2),
            "over_under": _cards_over_under(lam_home_yellow, lam_away_yellow),
            "home_dist":  home_yellow_dist,
            "away_dist":  away_yellow_dist,
        },
        "fouls": {
            "expected_home":  lam_home_fouls,
            "expected_away":  lam_away_fouls,
            "expected_total": round(lam_home_fouls + lam_away_fouls, 2),
        },
    }
