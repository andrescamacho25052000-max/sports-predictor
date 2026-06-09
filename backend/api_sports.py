import os
import time
import requests
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

API_KEY  = os.getenv("API_SPORTS_KEY")
BASE_URL = "https://v3.football.api-sports.io"
HEADERS  = {"x-apisports-key": API_KEY}

CURRENT_SEASON = 2025

# Liga BetPlay Dimayor — ID oficial en API-Sports
BETPLAY_LEAGUE_ID = 239

_cache: dict = {}
CACHE_TTL = 3600  # 1 hora — conservar las 100 req/día del plan gratis

# Estado de la cuota diaria
_quota = {
    "remaining": None,   # None = no consultado aún
    "exhausted": False,  # True cuando ya no hay requests disponibles
    "reset_at":  None,   # timestamp UTC de cuando se resetea
}


def quota_status() -> dict:
    """Devuelve el estado actual de la cuota de API-Sports."""
    return dict(_quota)


def _get(path: str) -> dict | None:
    global _quota

    # Si la cuota está agotada no hacemos la llamada
    if _quota["exhausted"]:
        print(f"[API-Sports] Cuota diaria agotada — omitiendo {path}")
        return None

    now = time.time()
    if path in _cache and now - _cache[path]["ts"] < CACHE_TTL:
        return _cache[path]["data"]

    try:
        r = requests.get(f"{BASE_URL}{path}", headers=HEADERS, timeout=10)

        # Actualizar estado de cuota desde los headers de respuesta
        remaining = r.headers.get("x-ratelimit-requests-remaining")
        if remaining is not None:
            _quota["remaining"] = int(remaining)
            if int(remaining) == 0:
                _quota["exhausted"] = True
                print("[API-Sports] ⚠ Cuota diaria agotada (0 requests restantes)")

        if r.status_code == 429:
            _quota["exhausted"] = True
            print("[API-Sports] ⚠ Rate limit HTTP 429 — cuota agotada")
            return None

        if r.status_code == 200:
            data = r.json()
            # Algunos endpoints devuelven el límite dentro del body
            errors = data.get("errors", {})
            if errors and ("rateLimit" in str(errors) or "quota" in str(errors).lower()):
                _quota["exhausted"] = True
                print(f"[API-Sports] ⚠ Cuota agotada por error en body: {errors}")
                return None
            _cache[path] = {"data": data, "ts": now}
            return data

        print(f"[API-Sports] Error {r.status_code} en {path}: {r.text[:200]}")
        return None

    except Exception as e:
        print(f"[API-Sports] Excepción en {path}: {e}")
        return None


def get_betplay_fixtures(next_n: int = 8) -> list[dict]:
    """
    Retorna los próximos partidos de la Liga BetPlay Dimayor.
    Si la cuota está agotada retorna lista vacía.
    """
    if _quota["exhausted"]:
        return []

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    data = _get(f"/fixtures?league={BETPLAY_LEAGUE_ID}&season={CURRENT_SEASON}&next={next_n}")

    if not data or not data.get("response"):
        return []

    matches = []
    for item in data["response"]:
        fixture  = item.get("fixture", {})
        teams    = item.get("teams", {})
        home     = teams.get("home", {})
        away     = teams.get("away", {})
        date_str = fixture.get("date", "")

        # Solo futuros
        try:
            match_dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            if match_dt <= datetime.now(timezone.utc):
                continue
        except Exception:
            continue

        matches.append({
            "home":    home.get("name", ""),
            "away":    away.get("name", ""),
            "home_id": None,   # API-Sports IDs ≠ football-data.org IDs
            "away_id": None,
            "date":    date_str,
            "fixture_id": fixture.get("id"),
        })

    return matches


def _clean_name(name: str) -> str:
    """Quita sufijos comunes para mejorar la búsqueda."""
    for suffix in [" FC", " AFC", " SC", " CF", " AC", " AS", " SD", " UD"]:
        name = name.replace(suffix, "")
    return name.strip()


def search_team(name: str) -> dict | None:
    """Busca un equipo por nombre. Retorna info del equipo y su estadio."""
    clean = _clean_name(name)

    for query in [name, clean]:
        data = _get(f"/teams?name={requests.utils.quote(query)}")
        if data and data.get("response"):
            t = data["response"][0]
            team  = t.get("team", {})
            venue = t.get("venue", {})
            return {
                "id":   team.get("id"),
                "name": team.get("name", name),
                "logo": team.get("logo", ""),
                "venue": {
                    "name":     venue.get("name", ""),
                    "city":     venue.get("city", ""),
                    "capacity": venue.get("capacity"),
                    "surface":  venue.get("surface", ""),
                    "image":    venue.get("image", ""),
                },
            }
    return None


def get_injuries(team_id: int) -> list[dict]:
    """Retorna lesionados y sancionados actuales del equipo."""
    data = _get(f"/injuries?team={team_id}&season={CURRENT_SEASON}")
    if not data or not data.get("response"):
        return []

    injured = []
    seen = set()
    for item in data["response"]:
        player = item.get("player", {})
        pname  = player.get("name", "Desconocido")
        reason = item.get("type", "Lesión")
        if pname not in seen:
            seen.add(pname)
            injured.append({
                "name":   pname,
                "reason": reason,
                "photo":  player.get("photo", ""),
            })
    return injured


def get_squad(team_id: int) -> list[dict]:
    """Retorna la plantilla completa del equipo."""
    data = _get(f"/players/squads?team={team_id}")
    if not data or not data.get("response"):
        return []

    players = []
    for item in data["response"]:
        for p in item.get("players", []):
            players.append({
                "name":     p.get("name", ""),
                "position": p.get("position", ""),
                "number":   p.get("number"),
                "age":      p.get("age"),
            })
    return players
