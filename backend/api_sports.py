import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY  = os.getenv("API_SPORTS_KEY")
BASE_URL = "https://v3.football.api-sports.io"
HEADERS  = {"x-apisports-key": API_KEY}

CURRENT_SEASON = 2024  # temporada 2024-2025 / 2025-2026

_cache: dict = {}
CACHE_TTL = 3600  # 1 hora — conservar las 100 req/día del plan gratis


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
        print(f"[API-Sports] Error {r.status_code} en {path}: {r.text[:200]}")
        return None
    except Exception as e:
        print(f"[API-Sports] Excepción en {path}: {e}")
        return None


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
