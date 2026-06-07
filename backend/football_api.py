import os
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("FOOTBALL_API_KEY")
BASE_URL = "https://api.football-data.org/v4"
HEADERS = {"X-Auth-Token": API_KEY}

# Todas las competiciones disponibles en el plan gratuito de football-data.org
COMPETITIONS = {
    # Europa — Ligas
    "Premier League":       "PL",
    "Championship":         "ELC",
    "La Liga":              "PD",
    "Bundesliga":           "BL1",
    "Serie A":              "SA",
    "Ligue 1":              "FL1",
    "Eredivisie":           "DED",
    "Primeira Liga":        "PPL",
    # Europa — Copas
    "Champions League":     "CL",
    "Eurocopa":             "EC",
    # Sudamérica
    "Copa Libertadores":    "CLI",
    # Brasil
    "Brasileirao Serie A":  "BSA",
    # Mundo
    "Mundial FIFA":         "WC",
}

# Agrupación por región (para mostrar en el frontend)
COMPETITION_REGIONS = {
    "Premier League":       "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Inglaterra",
    "Championship":         "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Inglaterra",
    "La Liga":              "🇪🇸 España",
    "Bundesliga":           "🇩🇪 Alemania",
    "Serie A":              "🇮🇹 Italia",
    "Ligue 1":              "🇫🇷 Francia",
    "Eredivisie":           "🇳🇱 Países Bajos",
    "Primeira Liga":        "🇵🇹 Portugal",
    "Champions League":     "🌍 Europa",
    "Eurocopa":             "🌍 Europa",
    "Copa Libertadores":    "🌎 Sudamérica",
    "Brasileirao Serie A":  "🇧🇷 Brasil",
    "Mundial FIFA":         "🌍 Mundo",
}

# Cache en memoria para respetar el límite de 10 req/min
_cache: dict = {}
CACHE_TTL = 300  # 5 minutos


def _get(path: str) -> dict | None:
    now = time.time()
    if path in _cache and now - _cache[path]["ts"] < CACHE_TTL:
        return _cache[path]["data"]

    try:
        r = requests.get(f"{BASE_URL}{path}", headers=HEADERS, timeout=10)
        if r.status_code == 200:
            data = r.json()
            _cache[path] = {"data": data, "ts": now}
            return data
        print(f"[API] Error {r.status_code} en {path}: {r.text[:200]}")
        return None
    except Exception as e:
        print(f"[API] Excepción en {path}: {e}")
        return None


def get_leagues() -> list[str]:
    return list(COMPETITIONS.keys())


def get_matches(league: str) -> list[dict]:
    code = COMPETITIONS.get(league)
    if not code:
        return []

    data = _get(f"/competitions/{code}/matches?status=SCHEDULED")
    if not data or "matches" not in data:
        return []

    matches = []
    for m in data["matches"][:10]:  # máximo 10 partidos
        home = m.get("homeTeam", {})
        away = m.get("awayTeam", {})
        if home.get("name") and away.get("name"):
            matches.append({
                "home": home["name"],
                "away": away["name"],
                "home_id": home.get("id"),
                "away_id": away.get("id"),
                "date": m.get("utcDate", ""),
            })
    return matches


def get_team_form(team_id: int, limit: int = 5) -> dict:
    """Retorna estadísticas recientes de un equipo."""
    data = _get(f"/teams/{team_id}/matches?status=FINISHED&limit={limit}")
    if not data or "matches" not in data:
        return _empty_form()

    matches = data["matches"][-limit:]
    wins = draws = losses = 0
    goals_scored = goals_conceded = 0

    for m in matches:
        home_id = m.get("homeTeam", {}).get("id")
        score = m.get("score", {}).get("fullTime", {})
        h = score.get("home", 0) or 0
        a = score.get("away", 0) or 0

        is_home = (home_id == team_id)
        gf = h if is_home else a
        gc = a if is_home else h
        goals_scored += gf
        goals_conceded += gc

        if gf > gc:
            wins += 1
        elif gf == gc:
            draws += 1
        else:
            losses += 1

    played = wins + draws + losses
    return {
        "wins_last5":          wins,
        "draws_last5":         draws,
        "losses_last5":        losses,
        "goals_scored_last5":  goals_scored,
        "goals_conceded_last5": goals_conceded,
        "possession_avg":      50,   # no disponible en plan gratis
        "shots_on_target_avg": 5.0,  # no disponible en plan gratis
        "injured_players":     0,    # no disponible en plan gratis
        "yellow_cards_last5":  0,
        "red_cards_last5":     0,
        "ranking":             10,   # se sobreescribe con standings
        "played":              played,
    }


def get_standings(league: str) -> dict[str, int]:
    """Retorna {nombre_equipo: posición} para una liga."""
    code = COMPETITIONS.get(league)
    if not code:
        return {}

    data = _get(f"/competitions/{code}/standings")
    if not data:
        return {}

    rankings = {}
    for group in data.get("standings", []):
        if group.get("type") == "TOTAL":
            for row in group.get("table", []):
                name = row.get("team", {}).get("name", "")
                pos = row.get("position", 99)
                if name:
                    rankings[name] = pos
    return rankings


def get_team_stats(team_name: str, team_id: int, league: str) -> dict:
    """Combina forma reciente + ranking para un equipo."""
    form = get_team_form(team_id)
    standings = get_standings(league)

    # Busca el ranking por nombre exacto o parcial
    ranking = standings.get(team_name)
    if not ranking:
        for name, pos in standings.items():
            if team_name.lower() in name.lower() or name.lower() in team_name.lower():
                ranking = pos
                break
    if ranking:
        form["ranking"] = ranking

    return form


def get_team_recent_matches(team_id: int, limit: int = 5) -> list:
    """Retorna el historial detallado de los últimos N partidos de un equipo."""
    data = _get(f"/teams/{team_id}/matches?status=FINISHED&limit={limit}")
    if not data or "matches" not in data:
        return []

    result = []
    for m in data["matches"][-limit:]:
        home_team = m.get("homeTeam", {})
        away_team = m.get("awayTeam", {})
        home_id_m = home_team.get("id")
        score = m.get("score", {}).get("fullTime", {})
        h = score.get("home", 0) or 0
        a = score.get("away", 0) or 0

        is_home = (home_id_m == team_id)
        gf = h if is_home else a
        gc = a if is_home else h
        opponent = away_team.get("name", "?") if is_home else home_team.get("name", "?")

        if gf > gc:
            res = "V"
        elif gf == gc:
            res = "E"
        else:
            res = "D"

        result.append({
            "opponent": opponent,
            "goals_for": gf,
            "goals_against": gc,
            "result": res,
            "was_home": is_home,
            "date": m.get("utcDate", "")[:10],
        })

    return result


def get_match_result(home_id: int, away_id: int, match_date: str) -> dict | None:
    """
    Busca el resultado real de un partido ya jugado.
    Revisa los últimos 20 partidos del equipo local filtrando por rival y fecha
    (tolerancia ±3 días por posibles aplazamientos).
    Devuelve {"home_goals": int, "away_goals": int, "winner": "Local"|"Empate"|"Visitante"}
    o None si aún no está disponible.
    """
    data = _get(f"/teams/{home_id}/matches?status=FINISHED&limit=20")
    if not data or "matches" not in data:
        return None

    try:
        target = datetime.strptime(match_date[:10], "%Y-%m-%d").date()
    except ValueError:
        return None

    for m in data["matches"]:
        h_id = m.get("homeTeam", {}).get("id")
        a_id = m.get("awayTeam", {}).get("id")

        if {h_id, a_id} != {home_id, away_id}:
            continue

        m_date_str = (m.get("utcDate") or "")[:10]
        try:
            m_date = datetime.strptime(m_date_str, "%Y-%m-%d").date()
            if abs((m_date - target).days) > 3:
                continue
        except ValueError:
            continue

        sc = m.get("score", {}).get("fullTime", {})
        h  = sc.get("home") or 0
        a  = sc.get("away") or 0

        if h > a:    winner = "Local"
        elif h == a: winner = "Empate"
        else:        winner = "Visitante"

        return {"home_goals": h, "away_goals": a, "winner": winner}

    return None


def get_h2h(team_id_1: int, team_id_2: int) -> dict | None:
    """Historial directo entre dos equipos desde el punto de vista de team_id_1."""
    data = _get(f"/teams/{team_id_1}/matches?status=FINISHED&limit=20")
    if not data or "matches" not in data:
        return None

    t1_wins = t2_wins = draws = found = 0

    for m in data["matches"]:
        h_id = m.get("homeTeam", {}).get("id")
        a_id = m.get("awayTeam", {}).get("id")
        if {h_id, a_id} != {team_id_1, team_id_2}:
            continue

        sc = m.get("score", {}).get("fullTime", {})
        h  = sc.get("home") or 0
        a  = sc.get("away") or 0
        gf = h if h_id == team_id_1 else a
        gc = a if h_id == team_id_1 else h

        if gf > gc:    t1_wins += 1
        elif gf == gc: draws   += 1
        else:          t2_wins += 1
        found += 1

    if found == 0:
        return None

    return {"wins": t1_wins, "draws": draws, "losses": t2_wins, "total": found}


def _empty_form() -> dict:
    return {
        "wins_last5": 2, "draws_last5": 1, "losses_last5": 2,
        "goals_scored_last5": 6, "goals_conceded_last5": 6,
        "possession_avg": 50, "shots_on_target_avg": 5.0,
        "injured_players": 0, "yellow_cards_last5": 0,
        "red_cards_last5": 0, "ranking": 10, "played": 5,
    }
