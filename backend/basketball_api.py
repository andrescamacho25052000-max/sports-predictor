"""
basketball_api.py
=================
Cliente de API-Sports Basketball (https://v1.basketball.api-sports.io) para la
NBA. Reutiliza la misma ``API_SPORTS_KEY`` que el fútbol.

Nota: el plan gratuito solo da acceso a temporadas 2022–2024. Por eso este
cliente se usa sobre todo para **construir** el modelo Elo a partir de partidos
históricos (un fetch por temporada devuelve todos sus partidos); las
predicciones en runtime no dependen de la API (usan los datos ya construidos).
"""

import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_SPORTS_KEY", "")
BASE_URL = "https://v1.basketball.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

NBA_LEAGUE_ID = 12

# Temporadas accesibles en el plan gratuito (de más antigua a más reciente).
BUILD_SEASONS = ["2022-2023", "2023-2024", "2024-2025"]

_cache: dict = {}
CACHE_TTL = 3600


def _get(path: str, params: dict) -> dict | None:
    """GET con caché simple. Devuelve el JSON o None si falla."""
    if not API_KEY:
        return None
    key = path + "?" + "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    now = time.time()
    if key in _cache and now - _cache[key]["ts"] < CACHE_TTL:
        return _cache[key]["data"]
    try:
        r = requests.get(f"{BASE_URL}{path}", params=params, headers=HEADERS, timeout=20)
        if r.status_code == 200:
            data = r.json()
            _cache[key] = {"data": data, "ts": now}
            return data
        print(f"[Basketball] Error {r.status_code} en {path}: {r.text[:200]}")
    except Exception as e:
        print(f"[Basketball] Excepción en {path}: {e}")
    return None


def get_season_games(season: str) -> list[dict]:
    """Trae todos los partidos NBA de una temporada.

    Args:
        season (str): Temporada en formato API-Sports, p.ej. "2024-2025".

    Returns:
        list[dict]: Lista de partidos normalizados con marcadores y estado.
        Solo incluye partidos con marcador (terminados).
    """
    data = _get("/games", {"league": NBA_LEAGUE_ID, "season": season})
    if not data or not data.get("response"):
        return []

    games = []
    for g in data["response"]:
        status = (g.get("status") or {}).get("short")
        scores = g.get("scores") or {}
        home_pts = (scores.get("home") or {}).get("total")
        away_pts = (scores.get("away") or {}).get("total")
        teams = g.get("teams") or {}
        if status not in ("FT", "AOT") or home_pts is None or away_pts is None:
            continue
        games.append({
            "date":      (g.get("date") or "")[:10],
            "home":      (teams.get("home") or {}).get("name", ""),
            "away":      (teams.get("away") or {}).get("name", ""),
            "home_id":   (teams.get("home") or {}).get("id"),
            "away_id":   (teams.get("away") or {}).get("id"),
            "home_logo": (teams.get("home") or {}).get("logo", ""),
            "away_logo": (teams.get("away") or {}).get("logo", ""),
            "home_pts":  int(home_pts),
            "away_pts":  int(away_pts),
        })
    games.sort(key=lambda x: x["date"])
    return games
