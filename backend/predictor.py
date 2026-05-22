from mock_data import TEAMS, HEAD_TO_HEAD

WEIGHTS = {
    "recent_form":    0.30,
    "squad_quality":  0.25,
    "home_advantage": 0.15,
    "injuries":       0.15,
    "head_to_head":   0.10,
    "conditions":     0.05,
}


# ─── Helpers de puntuación ────────────────────────────────────────────────────

def _form_score(team: dict) -> float:
    wins      = team["wins_last5"]
    draws     = team["draws_last5"]
    goals_diff = team["goals_scored_last5"] - team["goals_conceded_last5"]
    return wins * 3 + draws * 1 + goals_diff * 0.5


def _squad_score(team: dict) -> float:
    return (10 - team["ranking"]) * 2 + team["possession_avg"] * 0.1 + team["shots_on_target_avg"]


def _injury_penalty(team: dict) -> float:
    return team["injured_players"] * 3 + team.get("red_cards_last5", 0) * 2


def _h2h_score(home_name: str, away_name: str) -> tuple[float, float]:
    key         = (home_name, away_name)
    reverse_key = (away_name, home_name)
    h2h  = HEAD_TO_HEAD.get(key) or HEAD_TO_HEAD.get(reverse_key)
    if not h2h:
        return 5.0, 5.0
    total   = sum(h2h.values())
    vals    = list(h2h.values())
    home_w  = vals[0] if key in HEAD_TO_HEAD else vals[1]
    home_ratio = home_w / total if total else 0.5
    return home_ratio * 10, (1 - home_ratio) * 10


def _home_advantage_score(stadium: dict | None) -> tuple[float, str]:
    """
    Localía base = 10 pts.
    Se incrementa según la capacidad del estadio:
      > 70 000 → +4 pts  (ambiente brutal)
      > 50 000 → +2 pts
      < 20 000 → -2 pts  (estadio pequeño, menos presión)
    """
    base     = 10.0
    capacity = (stadium.get("capacity") or 30_000) if stadium else 30_000

    if capacity > 70_000:
        return base + 4, f"Estadio enorme ({capacity:,} personas) — presión masiva sobre el visitante"
    if capacity > 50_000:
        return base + 2, f"Estadio grande ({capacity:,} personas) — gran ambiente local"
    if capacity < 20_000:
        return base - 2, f"Estadio pequeño ({capacity:,} personas) — menor efecto de localía"
    return base, f"Estadio de {capacity:,} personas"


def _conditions_score(weather: dict | None, stadium: dict | None) -> tuple[float, float, str]:
    """
    Calcula bonus/penalización de condiciones para (local, visitante).
    Base: 5 pts cada uno (neutral).
    Factores reales aplicados:
      - Lluvia intensa  → local +2, visitante -2  (conoce mejor el terreno)
      - Lluvia leve     → local +1
      - Viento fuerte   → local +2, visitante -3
      - Viento moderado → local +1, visitante -1
      - Nevada          → local +3, visitante -3
      - Tormenta        → local +2, visitante -2
      - Césped artificial → local +2, visitante -2 (visitante menos adaptado)
    """
    home_bonus = 5.0
    away_bonus = 5.0
    details    = []

    if weather:
        precip = weather.get("precipitation", 0) or 0
        wind   = weather.get("windspeed",     0) or 0
        code   = weather.get("weathercode",   0) or 0

        # ── Lluvia ────────────────────────────────────────────────
        if code in (65, 82, 99) or precip > 15:
            home_bonus += 2
            away_bonus -= 2
            details.append(f"lluvia intensa ({precip:.1f}mm) — local conoce mejor el terreno mojado")
        elif code in (61, 63, 80, 81) or 5 < precip <= 15:
            home_bonus += 1
            details.append(f"lluvia moderada ({precip:.1f}mm)")
        elif code in (51, 53, 55) or 0 < precip <= 5:
            details.append(f"llovizna leve ({precip:.1f}mm)")

        # ── Viento ────────────────────────────────────────────────
        if wind > 50:
            home_bonus += 2
            away_bonus -= 3
            details.append(f"viento muy fuerte ({wind:.0f} km/h) — perjudica al visitante")
        elif wind > 30:
            home_bonus += 1
            away_bonus -= 1
            details.append(f"viento moderado ({wind:.0f} km/h)")

        # ── Nieve ─────────────────────────────────────────────────
        if code in (71, 73, 75):
            home_bonus += 3
            away_bonus -= 3
            details.append("nevada — gran ventaja para el local")

        # ── Tormenta ──────────────────────────────────────────────
        if code in (95, 99) and "lluvia intensa" not in " ".join(details):
            home_bonus += 2
            away_bonus -= 2
            details.append("tormenta eléctrica — condiciones muy adversas")

    # ── Superficie del estadio ────────────────────────────────────
    if stadium:
        surface = stadium.get("surface", "")
        if surface == "artificial turf":
            home_bonus += 2
            away_bonus -= 2
            details.append("césped artificial — visitante menos adaptado")
        elif surface == "hybrid grass":
            home_bonus += 0.5
            details.append("césped híbrido")

    if not details:
        details.append("condiciones ideales para el juego")

    # Determinar quién tiene ventaja
    detail_str = " · ".join(details)
    return home_bonus, away_bonus, detail_str


# ─── Función principal ────────────────────────────────────────────────────────

def predict(
    home_name:  str,
    away_name:  str,
    home_stats: dict = None,
    away_stats: dict = None,
    weather:    dict = None,
    stadium:    dict = None,
) -> dict:
    """
    Predice el resultado de un partido usando todos los datos disponibles.
    - home_stats / away_stats: forma reciente, ranking, lesiones (de las APIs)
    - weather: pronóstico del clima (Open-Meteo)
    - stadium: información del estadio (API-Sports)
    """
    home = home_stats or TEAMS.get(home_name) or _neutral_stats()
    away = away_stats or TEAMS.get(away_name) or _neutral_stats()

    home_score = 0.0
    away_score = 0.0
    factors    = []

    # ── 1. Forma reciente (30%) ───────────────────────────────────
    home_form = _form_score(home)
    away_form = _form_score(away)
    home_score += home_form * WEIGHTS["recent_form"]
    away_score += away_form * WEIGHTS["recent_form"]
    factors.append({
        "name":      "Forma reciente",
        "weight":    int(WEIGHTS["recent_form"] * 100),
        "advantage": home_name if home_form >= away_form else away_name,
        "detail":    f"{home_name}: {home['wins_last5']}V/{home['draws_last5']}E/{home['losses_last5']}D — "
                     f"{away_name}: {away['wins_last5']}V/{away['draws_last5']}E/{away['losses_last5']}D",
    })

    # ── 2. Calidad del plantel (25%) ──────────────────────────────
    home_squad = _squad_score(home)
    away_squad = _squad_score(away)
    home_score += home_squad * WEIGHTS["squad_quality"]
    away_score += away_squad * WEIGHTS["squad_quality"]
    factors.append({
        "name":      "Calidad del plantel",
        "weight":    int(WEIGHTS["squad_quality"] * 100),
        "advantage": home_name if home_squad >= away_squad else away_name,
        "detail":    f"Ranking {home_name} #{home['ranking']} — Ranking {away_name} #{away['ranking']}",
    })

    # ── 3. Localía + capacidad del estadio (15%) ──────────────────
    home_adv, adv_detail = _home_advantage_score(stadium)
    home_score += home_adv * WEIGHTS["home_advantage"]
    factors.append({
        "name":      "Ventaja de localía",
        "weight":    int(WEIGHTS["home_advantage"] * 100),
        "advantage": home_name,
        "detail":    adv_detail,
    })

    # ── 4. Lesiones (15%) ─────────────────────────────────────────
    home_inj = _injury_penalty(home)
    away_inj = _injury_penalty(away)
    home_score -= home_inj * WEIGHTS["injuries"]
    away_score -= away_inj * WEIGHTS["injuries"]
    if home_inj < away_inj:
        inj_adv = home_name
    elif away_inj < home_inj:
        inj_adv = away_name
    else:
        inj_adv = "Igual"
    factors.append({
        "name":      "Lesiones",
        "weight":    int(WEIGHTS["injuries"] * 100),
        "advantage": inj_adv,
        "detail":    f"{home_name}: {home['injured_players']} lesionados — {away_name}: {away['injured_players']} lesionados",
    })

    # ── 5. Historial directo (10%) ────────────────────────────────
    h2h_home, h2h_away = _h2h_score(home_name, away_name)
    home_score += h2h_home * WEIGHTS["head_to_head"]
    away_score += h2h_away * WEIGHTS["head_to_head"]
    factors.append({
        "name":      "Historial directo",
        "weight":    int(WEIGHTS["head_to_head"] * 100),
        "advantage": home_name if h2h_home >= h2h_away else away_name,
        "detail":    "Basado en enfrentamientos anteriores",
    })

    # ── 6. Clima y superficie (5%) ────────────────────────────────
    cond_home, cond_away, cond_detail = _conditions_score(weather, stadium)
    home_score += cond_home * WEIGHTS["conditions"]
    away_score += cond_away * WEIGHTS["conditions"]
    if cond_home > cond_away:
        cond_adv = home_name
    elif cond_away > cond_home:
        cond_adv = away_name
    else:
        cond_adv = "Igual"
    factors.append({
        "name":      "Clima y condiciones",
        "weight":    int(WEIGHTS["conditions"] * 100),
        "advantage": cond_adv,
        "detail":    cond_detail,
    })

    # ── Normalizar a probabilidades ───────────────────────────────
    total = home_score + away_score
    if total <= 0:
        raw_home = raw_away = 0.5
    else:
        raw_home = home_score / total
        raw_away = away_score / total

    diff      = abs(raw_home - raw_away)
    draw_prob = max(0.10, 0.30 - diff * 0.8)
    remaining = 1 - draw_prob
    denom     = (raw_home + raw_away) or 1
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
        "model":   "rule-based",
    }


def _neutral_stats() -> dict:
    return {
        "wins_last5": 2, "draws_last5": 1, "losses_last5": 2,
        "goals_scored_last5": 6, "goals_conceded_last5": 6,
        "possession_avg": 50, "shots_on_target_avg": 5.0,
        "injured_players": 0, "yellow_cards_last5": 0,
        "red_cards_last5": 0, "ranking": 10,
    }
