from mock_data import TEAMS, HEAD_TO_HEAD
from datetime import datetime

WEIGHTS = {
    "recent_form":    0.25,
    "home_away_form": 0.08,
    "squad_quality":  0.22,
    "home_advantage": 0.15,
    "injuries":       0.13,
    "head_to_head":   0.12,
    "conditions":     0.05,
}
# Suma total = 1.00


# ─── Helpers de puntuación ────────────────────────────────────────────────────

def _form_score(team: dict) -> float:
    wins       = team["wins_last5"]
    draws      = team["draws_last5"]
    goals_diff = team["goals_scored_last5"] - team["goals_conceded_last5"]
    return wins * 3 + draws * 1 + goals_diff * 0.5


def _squad_score(team: dict) -> float:
    return (10 - team["ranking"]) * 2 + team["possession_avg"] * 0.1 + team["shots_on_target_avg"]


def _injury_penalty(team: dict) -> float:
    return team["injured_players"] * 3 + team.get("red_cards_last5", 0) * 2


def _h2h_score(
    home_name: str,
    away_name: str,
    h2h_data: dict | None = None,
) -> tuple[float, float, str]:
    """
    Returns (home_score, away_score, detail).
    Usa datos reales de la API si están disponibles; si no, cae en mock data.
    """
    if h2h_data and h2h_data.get("total", 0) > 0:
        total     = h2h_data["total"]
        hw        = h2h_data["wins"]
        aw        = h2h_data["losses"]
        d         = h2h_data["draws"]
        home_rat  = hw / total
        away_rat  = aw / total
        detail    = f"{total} encuentros: {hw}V / {d}E / {aw}D para {home_name}"
        return home_rat * 10, away_rat * 10, detail

    # Fallback a datos mock
    key         = (home_name, away_name)
    reverse_key = (away_name, home_name)
    h2h         = HEAD_TO_HEAD.get(key) or HEAD_TO_HEAD.get(reverse_key)
    if not h2h:
        return 5.0, 5.0, "Sin historial directo disponible"

    total    = sum(h2h.values())
    vals     = list(h2h.values())
    home_w   = vals[0] if key in HEAD_TO_HEAD else vals[1]
    home_rat = home_w / total if total else 0.5
    detail   = f"Historial estimado — {home_name} gana {home_rat:.0%} de los cruces"
    return home_rat * 10, (1 - home_rat) * 10, detail


def _home_away_form_score(recent_matches: list, as_home: bool) -> float:
    """
    Puntaje (0-10) basado únicamente en partidos en casa (as_home=True)
    o fuera de casa (as_home=False).
    """
    filtered = [m for m in recent_matches if m.get("was_home") == as_home]
    if not filtered:
        return 5.0  # neutral cuando no hay datos
    wins  = sum(1 for m in filtered if m.get("result") == "V")
    draws = sum(1 for m in filtered if m.get("result") == "E")
    # Escala: cada victoria = 2 pts, empate = 1 pt; máximo posible = len*2
    return (wins * 2 + draws) / (len(filtered) * 2) * 10


def _rest_days_modifier(recent_matches: list, match_date: str) -> tuple[float, str]:
    """
    Penalización/bonus por días de descanso entre el último partido y este.
    Devuelve (modificador, detalle).
    """
    if not recent_matches or not match_date:
        return 0.0, ""

    dates = [m.get("date", "") for m in recent_matches if m.get("date")]
    if not dates:
        return 0.0, ""

    try:
        last   = datetime.strptime(max(dates)[:10], "%Y-%m-%d")
        target = datetime.strptime(match_date[:10], "%Y-%m-%d")
        days   = (target - last).days

        if days < 0:
            return 0.0, ""
        if days <= 2:
            return -2.0, f"{days}d de descanso — fatiga alta"
        if days <= 4:
            return -1.0, f"{days}d de descanso — algo justo"
        if days >= 10:
            return  1.0, f"{days}d de descanso — bien recuperados"
        return 0.0, f"{days}d de descanso"
    except Exception:
        return 0.0, ""


def _home_advantage_score(stadium: dict | None) -> tuple[float, str]:
    """
    Localía base = 10 pts.
    Se incrementa/disminuye según capacidad del estadio.
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
    Bonus/penalización por clima y superficie.
    Base: 5 pts cada equipo (neutral).
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
            home_bonus += 2; away_bonus -= 2
            details.append(f"lluvia intensa ({precip:.1f}mm) — local conoce mejor el terreno mojado")
        elif code in (61, 63, 80, 81) or 5 < precip <= 15:
            home_bonus += 1
            details.append(f"lluvia moderada ({precip:.1f}mm)")
        elif code in (51, 53, 55) or 0 < precip <= 5:
            details.append(f"llovizna leve ({precip:.1f}mm)")

        # ── Viento ────────────────────────────────────────────────
        if wind > 50:
            home_bonus += 2; away_bonus -= 3
            details.append(f"viento muy fuerte ({wind:.0f} km/h) — perjudica al visitante")
        elif wind > 30:
            home_bonus += 1; away_bonus -= 1
            details.append(f"viento moderado ({wind:.0f} km/h)")

        # ── Nieve ─────────────────────────────────────────────────
        if code in (71, 73, 75):
            home_bonus += 3; away_bonus -= 3
            details.append("nevada — gran ventaja para el local")

        # ── Tormenta ──────────────────────────────────────────────
        if code in (95, 99) and "lluvia intensa" not in " ".join(details):
            home_bonus += 2; away_bonus -= 2
            details.append("tormenta eléctrica — condiciones muy adversas")

    # ── Superficie del estadio ────────────────────────────────────
    if stadium:
        surface = stadium.get("surface", "")
        if surface == "artificial turf":
            home_bonus += 2; away_bonus -= 2
            details.append("césped artificial — visitante menos adaptado")
        elif surface == "hybrid grass":
            home_bonus += 0.5
            details.append("césped híbrido")

    if not details:
        details.append("condiciones ideales para el juego")

    return home_bonus, away_bonus, " · ".join(details)


# ─── Función principal ────────────────────────────────────────────────────────

def predict(
    home_name:  str,
    away_name:  str,
    home_stats: dict = None,
    away_stats: dict = None,
    weather:    dict = None,
    stadium:    dict = None,
    h2h_data:   dict = None,
    match_date: str  = "",
) -> dict:
    """
    Predice el resultado usando hasta 7 factores ponderados.
    - home_stats / away_stats: forma reciente, ranking, lesiones, recent_matches
    - weather: pronóstico Open-Meteo
    - stadium: info del estadio (API-Sports)
    - h2h_data: historial directo real (football-data.org)
    - match_date: YYYY-MM-DD para cálculo de días de descanso
    """
    home = home_stats or TEAMS.get(home_name) or _neutral_stats()
    away = away_stats or TEAMS.get(away_name) or _neutral_stats()

    home_recent = home.get("recent_matches", [])
    away_recent = away.get("recent_matches", [])

    home_score = 0.0
    away_score = 0.0
    factors    = []

    # ── 1. Forma reciente + días de descanso (25%) ────────────────
    home_form = _form_score(home)
    away_form = _form_score(away)

    home_rest_mod, home_rest_str = _rest_days_modifier(home_recent, match_date)
    away_rest_mod, away_rest_str = _rest_days_modifier(away_recent, match_date)

    home_form_adj = home_form + home_rest_mod
    away_form_adj = away_form + away_rest_mod

    home_score += home_form_adj * WEIGHTS["recent_form"]
    away_score += away_form_adj * WEIGHTS["recent_form"]

    rest_parts = []
    if home_rest_str:
        rest_parts.append(f"{home_name}: {home_rest_str}")
    if away_rest_str:
        rest_parts.append(f"{away_name}: {away_rest_str}")

    form_detail = (
        f"{home_name}: {home['wins_last5']}V/{home['draws_last5']}E/{home['losses_last5']}D"
        f" — {away_name}: {away['wins_last5']}V/{away['draws_last5']}E/{away['losses_last5']}D"
    )
    if rest_parts:
        form_detail += " · " + " · ".join(rest_parts)

    factors.append({
        "name":      "Forma reciente",
        "weight":    int(WEIGHTS["recent_form"] * 100),
        "advantage": home_name if home_form_adj >= away_form_adj else away_name,
        "detail":    form_detail,
    })

    # ── 2. Forma en casa / fuera (8%) ─────────────────────────────
    home_home_score = _home_away_form_score(home_recent, as_home=True)
    away_away_score = _home_away_form_score(away_recent, as_home=False)
    home_score += home_home_score * WEIGHTS["home_away_form"]
    away_score += away_away_score * WEIGHTS["home_away_form"]

    home_hg = [m for m in home_recent if m.get("was_home")]
    away_ag = [m for m in away_recent if not m.get("was_home")]
    home_hw = sum(1 for m in home_hg if m.get("result") == "V")
    away_aw = sum(1 for m in away_ag if m.get("result") == "V")

    haf_home_str = f"{home_hw}/{len(home_hg)} vic. de local" if home_hg else "sin datos de local"
    haf_away_str = f"{away_aw}/{len(away_ag)} vic. de visitante" if away_ag else "sin datos de visitante"

    factors.append({
        "name":      "Forma en casa / fuera",
        "weight":    int(WEIGHTS["home_away_form"] * 100),
        "advantage": home_name if home_home_score >= away_away_score else away_name,
        "detail":    f"{home_name}: {haf_home_str} — {away_name}: {haf_away_str}",
    })

    # ── 3. Calidad del plantel (22%) ──────────────────────────────
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

    # ── 4. Localía + capacidad del estadio (15%) ──────────────────
    home_adv, adv_detail = _home_advantage_score(stadium)
    home_score += home_adv * WEIGHTS["home_advantage"]
    factors.append({
        "name":      "Ventaja de localía",
        "weight":    int(WEIGHTS["home_advantage"] * 100),
        "advantage": home_name,
        "detail":    adv_detail,
    })

    # ── 5. Lesiones (13%) ─────────────────────────────────────────
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

    # ── 6. Historial directo (12%) ────────────────────────────────
    h2h_home, h2h_away, h2h_detail = _h2h_score(home_name, away_name, h2h_data)
    home_score += h2h_home * WEIGHTS["head_to_head"]
    away_score += h2h_away * WEIGHTS["head_to_head"]
    factors.append({
        "name":      "Historial directo",
        "weight":    int(WEIGHTS["head_to_head"] * 100),
        "advantage": home_name if h2h_home >= h2h_away else away_name,
        "detail":    h2h_detail,
    })

    # ── 7. Clima y condiciones (5%) ───────────────────────────────
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
        "model":   "rule-based v2",
    }


def _neutral_stats() -> dict:
    return {
        "wins_last5": 2, "draws_last5": 1, "losses_last5": 2,
        "goals_scored_last5": 6, "goals_conceded_last5": 6,
        "possession_avg": 50, "shots_on_target_avg": 5.0,
        "injured_players": 0, "yellow_cards_last5": 0,
        "red_cards_last5": 0, "ranking": 10,
        "recent_matches": [],
    }
