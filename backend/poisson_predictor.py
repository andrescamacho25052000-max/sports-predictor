"""
poisson_predictor.py — Predicción de goles y mercados de apuesta usando distribución de Poisson.

La distribución de Poisson es el estándar de la industria para calcular
probabilidades de marcadores en fútbol. Todas las casas de apuestas la usan.

Lógica:
  λ_local    = promedio de goles del local   × factor defensivo del visitante × ventaja local
  λ_visitante = promedio de goles del visitante × factor defensivo del local

  P(local marca X goles, visitante marca Y goles) = Poisson(X, λ_local) × Poisson(Y, λ_visitante)

Con esa matriz de probabilidades calculamos todos los mercados.
"""
import math
from itertools import product

# Ventaja de localía (los equipos locales meten ~15% más goles históricamente)
HOME_ADVANTAGE = 1.15

# Goles por partido de referencia si faltan datos (liga tope europeo)
LEAGUE_AVG_SCORED   = 1.45   # goles del local por partido
LEAGUE_AVG_CONCEDED = 1.15   # goles del visitante por partido

# Máximo de goles que modelamos por equipo (7 es suficiente: P(>7) < 0.01%)
MAX_GOALS = 7


# ─── Núcleo matemático ────────────────────────────────────────────────────────

def _poisson_pmf(k: int, lam: float) -> float:
    """Probabilidad de exactamente k eventos con tasa lambda."""
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def _score_matrix(lam_h: float, lam_a: float) -> list[list[float]]:
    """
    Matriz de probabilidades [home_goals][away_goals].
    score_matrix[2][1] = P(2-1)
    """
    return [
        [_poisson_pmf(h, lam_h) * _poisson_pmf(a, lam_a)
         for a in range(MAX_GOALS + 1)]
        for h in range(MAX_GOALS + 1)
    ]


def _calc_lambdas(home_stats: dict, away_stats: dict) -> tuple[float, float]:
    """
    Calcula λ_home y λ_away a partir de los stats de cada equipo.
    Usa los últimos 5 partidos y ajusta por ventaja de localía.
    """
    # Goles por partido en los últimos 5
    h_scored   = home_stats.get("goals_scored_last5",  LEAGUE_AVG_SCORED   * 5) / 5
    h_conceded = home_stats.get("goals_conceded_last5", LEAGUE_AVG_CONCEDED * 5) / 5
    a_scored   = away_stats.get("goals_scored_last5",  LEAGUE_AVG_CONCEDED * 5) / 5
    a_conceded = away_stats.get("goals_conceded_last5", LEAGUE_AVG_SCORED   * 5) / 5

    # λ = promedio de ataque × factor defensivo del rival (Dixon-Coles simplificado)
    lam_h = ((h_scored + a_conceded) / 2) * HOME_ADVANTAGE
    lam_a =  (a_scored + h_conceded) / 2

    # Acotar entre valores razonables (evitar λ=0 o extremos)
    lam_h = max(0.3, min(lam_h, 5.0))
    lam_a = max(0.3, min(lam_a, 5.0))

    return lam_h, lam_a


# ─── Mercados ─────────────────────────────────────────────────────────────────

def _market_1x2(matrix: list) -> dict:
    """Resultado final: Local / Empate / Visitante."""
    home_win = draw = away_win = 0.0
    for h in range(MAX_GOALS + 1):
        for a in range(MAX_GOALS + 1):
            p = matrix[h][a]
            if h > a:   home_win += p
            elif h == a: draw    += p
            else:        away_win += p
    return {
        "home_win": round(home_win * 100, 1),
        "draw":     round(draw     * 100, 1),
        "away_win": round(away_win * 100, 1),
    }


def _market_over_under(matrix: list) -> dict:
    """Over/Under para 0.5, 1.5, 2.5, 3.5, 4.5 goles totales."""
    result = {}
    for line in [0.5, 1.5, 2.5, 3.5, 4.5]:
        over = sum(
            matrix[h][a]
            for h in range(MAX_GOALS + 1)
            for a in range(MAX_GOALS + 1)
            if (h + a) > line
        )
        result[f"over_{line}"]  = round(over * 100, 1)
        result[f"under_{line}"] = round((1 - over) * 100, 1)
    return result


def _market_btts(matrix: list) -> dict:
    """Ambos equipos marcan (Both Teams To Score)."""
    btts = sum(
        matrix[h][a]
        for h in range(1, MAX_GOALS + 1)
        for a in range(1, MAX_GOALS + 1)
    )
    return {
        "yes": round(btts * 100, 1),
        "no":  round((1 - btts) * 100, 1),
    }


def _market_exact_score(matrix: list, top_n: int = 10) -> list[dict]:
    """Marcadores exactos más probables."""
    scores = []
    for h in range(MAX_GOALS + 1):
        for a in range(MAX_GOALS + 1):
            scores.append({
                "score": f"{h}-{a}",
                "home":  h,
                "away":  a,
                "prob":  round(matrix[h][a] * 100, 2),
            })
    scores.sort(key=lambda x: -x["prob"])
    return scores[:top_n]


def _market_ht(lam_h: float, lam_a: float) -> dict:
    """
    Resultado al descanso.
    Históricamente ~38% de los goles caen en la primera mitad.
    """
    lam_ht_h = lam_h * 0.38
    lam_ht_a = lam_a * 0.38
    matrix_ht = _score_matrix(lam_ht_h, lam_ht_a)
    res = _market_1x2(matrix_ht)
    return {
        "home_win": res["home_win"],
        "draw":     res["draw"],
        "away_win": res["away_win"],
    }


def _market_team_goals(lam: float, label: str) -> dict:
    """
    Líneas individuales de goles para un equipo:
    over/under 0.5 y 1.5.
    """
    p0 = _poisson_pmf(0, lam)
    p1 = _poisson_pmf(1, lam)
    over_05  = round((1 - p0)       * 100, 1)
    over_15  = round((1 - p0 - p1)  * 100, 1)
    return {
        f"{label}_over_0_5":  over_05,
        f"{label}_under_0_5": round(p0 * 100, 1),
        f"{label}_over_1_5":  over_15,
        f"{label}_under_1_5": round((p0 + p1) * 100, 1),
    }


def _market_clean_sheet(lam_opponent: float) -> dict:
    """
    Probabilidad de portería a cero para un equipo
    (equivale a que el rival marque 0 goles).
    """
    p_zero = _poisson_pmf(0, lam_opponent)
    return {
        "yes": round(p_zero * 100, 1),
        "no":  round((1 - p_zero) * 100, 1),
    }


def _expected_goals(lam_h: float, lam_a: float) -> dict:
    """xG esperado — valor más probable de goles totales y por equipo."""
    return {
        "home":  round(lam_h, 2),
        "away":  round(lam_a, 2),
        "total": round(lam_h + lam_a, 2),
    }


# ─── Función principal ────────────────────────────────────────────────────────

def predict_poisson(home_stats: dict, away_stats: dict) -> dict:
    """
    Genera todos los mercados de apuesta basados en Poisson.

    Parámetros:
        home_stats / away_stats : dict con al menos
            goals_scored_last5, goals_conceded_last5

    Retorna:
        dict con todos los mercados listos para el frontend.
    """
    lam_h, lam_a = _calc_lambdas(home_stats, away_stats)
    matrix = _score_matrix(lam_h, lam_a)

    return {
        "expected_goals":  _expected_goals(lam_h, lam_a),
        "result_1x2":      _market_1x2(matrix),
        "over_under":      _market_over_under(matrix),
        "btts":            _market_btts(matrix),
        "exact_score":     _market_exact_score(matrix, top_n=10),
        "half_time":       _market_ht(lam_h, lam_a),
        "home_goals":      _market_team_goals(lam_h, "home"),
        "away_goals":      _market_team_goals(lam_a, "away"),
        "home_clean_sheet": _market_clean_sheet(lam_a),
        "away_clean_sheet": _market_clean_sheet(lam_h),
    }
