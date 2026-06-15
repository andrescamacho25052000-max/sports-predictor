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

# Calibración para fútbol de selecciones / Mundial: marca menos goles que las
# ligas de clubes con las que se calibró el prior. Sin esto el modelo sobre-
# estima los goles (validado: 4 de 5 partidos de grupos terminaron Under 2.5
# mientras el modelo promediaba 2.96 goles esperados vs 2.4 reales).
GOALS_DAMP_NEUTRAL = 0.90

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


def _team_rates(stats: dict, prior_scored: float, prior_conceded: float) -> tuple[float, float]:
    """
    Goles por partido (anotados, recibidos) de un equipo.
    Divide entre los partidos realmente jugados (no 5 fijo) y mezcla con el
    promedio de liga como prior bayesiano para muestras chicas: con 0 partidos
    devuelve el prior puro; con pocos partidos, un punto intermedio.
    """
    played   = stats.get("played", 5) or 0
    scored   = stats.get("goals_scored_last5")
    conceded = stats.get("goals_conceded_last5")

    if played <= 0 or scored is None or conceded is None:
        return prior_scored, prior_conceded

    PRIOR_WEIGHT = 2  # equivale a 2 partidos de evidencia al promedio de liga
    rate_scored   = (scored   + prior_scored   * PRIOR_WEIGHT) / (played + PRIOR_WEIGHT)
    rate_conceded = (conceded + prior_conceded * PRIOR_WEIGHT) / (played + PRIOR_WEIGHT)
    return rate_scored, rate_conceded


# Peso del Elo al repartir los goles esperados entre los dos equipos.
# 0 = solo forma reciente (comportamiento viejo); 1 = solo Elo.
ELO_BLEND = 0.5
# Ventaja de localía expresada en puntos Elo (0 en cancha neutral).
HOME_ADV_ELO = 65


def _calc_lambdas(home_stats: dict, away_stats: dict, neutral: bool = False) -> tuple[float, float]:
    """
    Calcula λ_home y λ_away a partir de los stats de cada equipo.
    - La forma reciente (goles marcados/recibidos) fija el TOTAL de goles esperados.
    - Ese total se reparte entre los dos equipos mezclando forma + Elo (fuerza
      relativa), para que el favorito según Elo reciba más xG aunque su forma
      reciente de goles sea pobre.
    - En cancha neutral (p.ej. Mundial) no se aplica ventaja de localía.
    """
    h_scored, h_conceded = _team_rates(home_stats, LEAGUE_AVG_SCORED,   LEAGUE_AVG_CONCEDED)
    a_scored, a_conceded = _team_rates(away_stats, LEAGUE_AVG_CONCEDED, LEAGUE_AVG_SCORED)

    home_mult = 1.0 if neutral else HOME_ADVANTAGE

    # λ base por forma (Dixon-Coles simplificado)
    lam_h = ((h_scored + a_conceded) / 2) * home_mult
    lam_a =  (a_scored + h_conceded) / 2

    # ── Ajuste por Elo ────────────────────────────────────────────────────
    # Si ambos equipos traen rating, se conserva el total de goles de la forma
    # pero se reparte según una mezcla de forma + fuerza relativa (Elo).
    elo_h = home_stats.get("elo")
    elo_a = away_stats.get("elo")
    if elo_h and elo_a:
        total = lam_h + lam_a
        if total > 0:
            ha = 0 if neutral else HOME_ADV_ELO
            d = (elo_h + ha) - elo_a
            share_h_elo  = 1 / (1 + 10 ** (-d / 400))   # 0..1 según Elo
            share_h_form = lam_h / total
            share_h = (1 - ELO_BLEND) * share_h_form + ELO_BLEND * share_h_elo
            lam_h = total * share_h
            lam_a = total * (1 - share_h)

    # Calibración de goles para selecciones (Mundial = cancha neutral):
    # el entorno goleador es más bajo que en ligas de clubes.
    if neutral:
        lam_h *= GOALS_DAMP_NEUTRAL
        lam_a *= GOALS_DAMP_NEUTRAL

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


def _market_handicap(matrix: list) -> dict:
    """
    Hándicap asiático de línea media (sin empate/reembolso) para las líneas
    más usadas. Se deriva de la matriz de marcadores sumando por margen
    (goles_local − goles_visitante).
    """
    margin: dict[int, float] = {}
    for h in range(MAX_GOALS + 1):
        for a in range(MAX_GOALS + 1):
            margin[h - a] = margin.get(h - a, 0.0) + matrix[h][a]

    def ge(x: int) -> float:   # P(margen ≥ x)  → local cubre el hándicap
        return round(sum(p for m, p in margin.items() if m >= x) * 100, 1)

    def le(x: int) -> float:   # P(margen ≤ x)  → visitante cubre el hándicap
        return round(sum(p for m, p in margin.items() if m <= x) * 100, 1)

    return {
        # Local con desventaja (debe ganar por margen) o ventaja (colchón)
        "home_-2.5": ge(3),    # gana por 3+
        "home_-1.5": ge(2),    # gana por 2+
        "home_+1.5": ge(-1),   # no pierde por 2+
        "home_+2.5": ge(-2),   # no pierde por 3+
        # Visitante con desventaja o ventaja
        "away_-2.5": le(-3),   # gana por 3+
        "away_-1.5": le(-2),   # gana por 2+
        "away_+1.5": le(1),    # no pierde por 2+
        "away_+2.5": le(2),    # no pierde por 3+
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

def predict_poisson(home_stats: dict, away_stats: dict, neutral: bool = False) -> dict:
    """
    Genera todos los mercados de apuesta basados en Poisson.

    Parámetros:
        home_stats / away_stats : dict con al menos
            goals_scored_last5, goals_conceded_last5 (y opcionalmente "elo")
        neutral : True en partidos a cancha neutral (no se aplica localía)

    Retorna:
        dict con todos los mercados listos para el frontend.
    """
    lam_h, lam_a = _calc_lambdas(home_stats, away_stats, neutral=neutral)
    matrix = _score_matrix(lam_h, lam_a)

    return {
        "expected_goals":  _expected_goals(lam_h, lam_a),
        "result_1x2":      _market_1x2(matrix),
        "over_under":      _market_over_under(matrix),
        "btts":            _market_btts(matrix),
        "exact_score":     _market_exact_score(matrix, top_n=10),
        "half_time":       _market_ht(lam_h, lam_a),
        "handicap":        _market_handicap(matrix),
        "home_goals":      _market_team_goals(lam_h, "home"),
        "away_goals":      _market_team_goals(lam_a, "away"),
        "home_clean_sheet": _market_clean_sheet(lam_a),
        "away_clean_sheet": _market_clean_sheet(lam_h),
    }
