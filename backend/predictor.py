from mock_data import TEAMS, HEAD_TO_HEAD

WEIGHTS = {
    "recent_form":    0.30,
    "squad_quality":  0.25,
    "home_advantage": 0.15,
    "injuries":       0.15,
    "head_to_head":   0.10,
    "conditions":     0.05,
}


def _form_score(team: dict) -> float:
    wins = team["wins_last5"]
    draws = team["draws_last5"]
    goals_diff = team["goals_scored_last5"] - team["goals_conceded_last5"]
    return wins * 3 + draws * 1 + goals_diff * 0.5


def _squad_score(team: dict) -> float:
    return (10 - team["ranking"]) * 2 + team["possession_avg"] * 0.1 + team["shots_on_target_avg"]


def _injury_penalty(team: dict) -> float:
    return team["injured_players"] * 3 + team.get("red_cards_last5", 0) * 2


def _h2h_score(home_name: str, away_name: str) -> tuple[float, float]:
    key = (home_name, away_name)
    reverse_key = (away_name, home_name)
    h2h = HEAD_TO_HEAD.get(key) or HEAD_TO_HEAD.get(reverse_key)
    if not h2h:
        return 5.0, 5.0
    total = sum(h2h.values())
    vals = list(h2h.values())
    home_w = vals[0] if key in HEAD_TO_HEAD else vals[1]
    home_ratio = home_w / total if total else 0.5
    return home_ratio * 10, (1 - home_ratio) * 10


def predict(home_name: str, away_name: str, home_stats: dict = None, away_stats: dict = None) -> dict:
    """
    Predice el resultado de un partido.
    Acepta stats reales (de la API) o usa datos mock como fallback.
    """
    # Usa stats reales si se proveen, si no busca en mock_data
    home = home_stats or TEAMS.get(home_name)
    away = away_stats or TEAMS.get(away_name)

    # Si no hay datos de ningún lado, usa valores neutros
    if not home:
        home = _neutral_stats()
    if not away:
        away = _neutral_stats()

    home_score = 0.0
    away_score = 0.0
    factors = []

    # Forma reciente (30%)
    home_form = _form_score(home)
    away_form = _form_score(away)
    home_score += home_form * WEIGHTS["recent_form"]
    away_score += away_form * WEIGHTS["recent_form"]
    winner_form = home_name if home_form >= away_form else away_name
    factors.append({
        "name": "Forma reciente",
        "weight": int(WEIGHTS["recent_form"] * 100),
        "advantage": winner_form,
        "detail": f"{home_name}: {home['wins_last5']}V/{home['draws_last5']}E/{home['losses_last5']}D — "
                  f"{away_name}: {away['wins_last5']}V/{away['draws_last5']}E/{away['losses_last5']}D",
    })

    # Calidad del plantel (25%)
    home_squad = _squad_score(home)
    away_squad = _squad_score(away)
    home_score += home_squad * WEIGHTS["squad_quality"]
    away_score += away_squad * WEIGHTS["squad_quality"]
    winner_squad = home_name if home_squad >= away_squad else away_name
    factors.append({
        "name": "Calidad del plantel",
        "weight": int(WEIGHTS["squad_quality"] * 100),
        "advantage": winner_squad,
        "detail": f"Ranking {home_name} #{home['ranking']} — Ranking {away_name} #{away['ranking']}",
    })

    # Localía (15%)
    home_score += 10 * WEIGHTS["home_advantage"]
    factors.append({
        "name": "Ventaja de localía",
        "weight": int(WEIGHTS["home_advantage"] * 100),
        "advantage": home_name,
        "detail": f"{home_name} juega en casa",
    })

    # Lesiones (15%)
    home_inj = _injury_penalty(home)
    away_inj = _injury_penalty(away)
    home_score -= home_inj * WEIGHTS["injuries"]
    away_score -= away_inj * WEIGHTS["injuries"]
    if home_inj < away_inj:
        inj_advantage = home_name
    elif away_inj < home_inj:
        inj_advantage = away_name
    else:
        inj_advantage = "Igual"
    factors.append({
        "name": "Lesiones",
        "weight": int(WEIGHTS["injuries"] * 100),
        "advantage": inj_advantage,
        "detail": f"{home_name}: {home['injured_players']} lesionados — {away_name}: {away['injured_players']} lesionados",
    })

    # Historial directo (10%)
    h2h_home, h2h_away = _h2h_score(home_name, away_name)
    home_score += h2h_home * WEIGHTS["head_to_head"]
    away_score += h2h_away * WEIGHTS["head_to_head"]
    h2h_winner = home_name if h2h_home >= h2h_away else away_name
    factors.append({
        "name": "Historial directo",
        "weight": int(WEIGHTS["head_to_head"] * 100),
        "advantage": h2h_winner,
        "detail": "Basado en enfrentamientos anteriores",
    })

    # Clima y condiciones (5%) — neutral
    home_score += 5 * WEIGHTS["conditions"]
    away_score += 5 * WEIGHTS["conditions"]
    factors.append({
        "name": "Clima y condiciones",
        "weight": int(WEIGHTS["conditions"] * 100),
        "advantage": "Igual",
        "detail": "Condiciones normales de juego",
    })

    # Normalizar a probabilidades
    total = home_score + away_score
    if total <= 0:
        raw_home, raw_away = 0.5, 0.5
    else:
        raw_home = home_score / total
        raw_away = away_score / total

    diff = abs(raw_home - raw_away)
    draw_prob = max(0.10, 0.30 - diff * 0.8)
    remaining = 1 - draw_prob
    denom = raw_home + raw_away if (raw_home + raw_away) > 0 else 1
    home_prob = raw_home * remaining / denom
    away_prob = raw_away * remaining / denom

    return {
        "home_team": home_name,
        "away_team": away_name,
        "probabilities": {
            "home_win": round(home_prob * 100, 1),
            "draw":     round(draw_prob * 100, 1),
            "away_win": round(away_prob * 100, 1),
        },
        "factors": factors,
        "model": "rule-based",
    }


def _neutral_stats() -> dict:
    return {
        "wins_last5": 2, "draws_last5": 1, "losses_last5": 2,
        "goals_scored_last5": 6, "goals_conceded_last5": 6,
        "possession_avg": 50, "shots_on_target_avg": 5.0,
        "injured_players": 0, "yellow_cards_last5": 0,
        "red_cards_last5": 0, "ranking": 10,
    }
