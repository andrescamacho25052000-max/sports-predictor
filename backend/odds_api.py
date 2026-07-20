"""
odds_api.py
===========
Cliente de The Odds API (https://the-odds-api.com) para traer cuotas reales de
casas de apuestas y calcular automáticamente el valor esperado (EV) de cada
mercado contra la probabilidad estimada por el modelo.

Diseño (igual que ``api_sports.py``):
- Si no hay ``ODDS_API_KEY`` configurada, todas las funciones degradan a None
  sin lanzar errores (la app sigue funcionando con entrada manual de cuotas).
- Caché en memoria para conservar la cuota del plan gratuito.
- La cuota restante se rastrea con los headers de respuesta de la API.

The Odds API devuelve cuotas en formato decimal por casa de apuestas. Para cada
mercado tomamos la **mejor cuota disponible** (la más alta), que es la más
favorable para el apostador.
"""

import os
import time
import unicodedata

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("ODDS_API_KEY", "")
BASE_URL = "https://api.the-odds-api.com/v4"

# Regiones de casas de apuestas a consultar. "eu,uk" da buena cobertura y suele
# incluir cuotas comparables a las de Betplay. Configurable por entorno.
REGIONS = os.getenv("ODDS_API_REGIONS", "eu,uk")

_cache: dict = {}
CACHE_TTL = 900  # 15 min — las cuotas cambian, pero el plan free es limitado

# Estado de la cuota mensual del plan
_quota = {
    "remaining": None,   # None = aún no consultado
    "used": None,
    "exhausted": False,
}

# Mapa de nombre de liga (interno de la app) → "sport key" de The Odds API.
# Si una liga no está acá, get_match_odds degrada a None silenciosamente.
LEAGUE_SPORT_KEYS = {
    "Premier League":        "soccer_epl",
    "La Liga":               "soccer_spain_la_liga",
    "Bundesliga":            "soccer_germany_bundesliga",
    "Serie A":               "soccer_italy_serie_a",
    "Ligue 1":               "soccer_france_ligue_one",
    "Champions League":      "soccer_uefa_champs_league",
    "Eredivisie":            "soccer_netherlands_eredivisie",
    "Primeira Liga":         "soccer_portugal_primeira_liga",
    "Championship":          "soccer_efl_champ",
    "Brasileirao Serie A":   "soccer_brazil_campeonato",
    "Copa Libertadores":     "soccer_conmebol_copa_libertadores",
    "Liga BetPlay":          "soccer_colombia_primera_a",
    "Mundial FIFA":          "soccer_fifa_world_cup",
    "Eurocopa":              "soccer_uefa_european_championship",
    "NBA":                   "basketball_nba",
}


def quota_status() -> dict:
    """Devuelve el estado actual de la cuota de The Odds API.

    Returns:
        dict: Copia de ``{"remaining", "used", "exhausted"}``.
    """
    return dict(_quota)


def is_configured() -> bool:
    """Indica si hay una API key configurada.

    Returns:
        bool: True si ``ODDS_API_KEY`` está presente.
    """
    return bool(API_KEY)


def sport_key_for(league: str) -> str | None:
    """Mapea el nombre de liga interno al sport key de The Odds API.

    Args:
        league (str): Nombre de la liga tal como lo usa la app.

    Returns:
        str | None: El sport key, o None si la liga no está mapeada.
    """
    return LEAGUE_SPORT_KEYS.get(league)


def expected_value(prob_pct: float, decimal_odds: float) -> float:
    """Calcula el valor esperado (EV) por unidad apostada.

    EV = P(ganar) * (cuota - 1) - P(perder)  ==  P * cuota - 1

    Args:
        prob_pct (float): Probabilidad estimada por el modelo, en % (0-100).
        decimal_odds (float): Cuota decimal ofrecida por la casa.

    Returns:
        float: EV por unidad apostada. Positivo = apuesta con valor.
    """
    p = max(0.0, min(1.0, prob_pct / 100.0))
    return round(p * decimal_odds - 1.0, 4)


def _norm(s: str) -> str:
    """Normaliza un nombre de equipo para comparar (minúsculas, sin acentos)."""
    s = (s or "").lower().strip()
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    for suffix in [" fc", " afc", " sc", " cf", " ac", " as", " sd", " ud"]:
        if s.endswith(suffix):
            s = s[: -len(suffix)]
    return s.strip()


def _names_match(want: str, got: str) -> bool:
    """True si dos nombres de equipo normalizados se solapan."""
    w, g = _norm(want), _norm(got)
    return bool(w) and bool(g) and (w in g or g in w)


def _get(path: str, params: dict) -> list | dict | None:
    """GET con caché y rastreo de cuota. Devuelve el JSON o None si falla."""
    global _quota

    if not API_KEY:
        return None
    if _quota["exhausted"]:
        print(f"[OddsAPI] Cuota agotada — omitiendo {path}")
        return None

    cache_key = path + "?" + "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    now = time.time()
    if cache_key in _cache and now - _cache[cache_key]["ts"] < CACHE_TTL:
        return _cache[cache_key]["data"]

    try:
        r = requests.get(f"{BASE_URL}{path}", params={**params, "apiKey": API_KEY}, timeout=10)

        remaining = r.headers.get("x-requests-remaining")
        used = r.headers.get("x-requests-used")
        if remaining is not None:
            _quota["remaining"] = int(float(remaining))
            if _quota["remaining"] <= 0:
                _quota["exhausted"] = True
                print("[OddsAPI] ⚠ Cuota mensual agotada (0 requests restantes)")
        if used is not None:
            _quota["used"] = int(float(used))

        if r.status_code == 401:
            print("[OddsAPI] ⚠ API key inválida (401)")
            return None
        if r.status_code == 429:
            _quota["exhausted"] = True
            print("[OddsAPI] ⚠ Rate limit HTTP 429")
            return None
        if r.status_code == 200:
            data = r.json()
            _cache[cache_key] = {"data": data, "ts": now}
            return data

        print(f"[OddsAPI] Error {r.status_code} en {path}: {r.text[:200]}")
        return None
    except Exception as e:
        print(f"[OddsAPI] Excepción en {path}: {e}")
        return None


def _best_h2h(bookmakers: list, home: str, away: str) -> dict | None:
    """Extrae la mejor cuota 1X2 (home/draw/away) entre todas las casas.

    Args:
        bookmakers (list): Lista de casas con sus mercados (formato Odds API).
        home (str): Nombre del equipo local del partido.
        away (str): Nombre del equipo visitante del partido.

    Returns:
        dict | None: ``{"home", "draw", "away"}`` con la mejor cuota decimal de
        cada resultado, o None si no hay mercado h2h disponible.
    """
    best = {"home": 0.0, "draw": 0.0, "away": 0.0}
    found = False
    for bk in bookmakers or []:
        for market in bk.get("markets", []):
            if market.get("key") != "h2h":
                continue
            for oc in market.get("outcomes", []):
                name = oc.get("name", "")
                price = oc.get("price")
                if not isinstance(price, (int, float)):
                    continue
                if _norm(name) == "draw" or _names_match("draw", name):
                    slot = "draw"
                elif _names_match(home, name):
                    slot = "home"
                elif _names_match(away, name):
                    slot = "away"
                else:
                    continue
                if price > best[slot]:
                    best[slot] = float(price)
                    found = True
    return best if found and all(best.values()) else None


def _best_totals(bookmakers: list) -> dict:
    """Extrae la mejor cuota Over/Under de goles por línea.

    Args:
        bookmakers (list): Lista de casas con sus mercados (formato Odds API).

    Returns:
        dict: ``{line: {"over": odds, "under": odds}}``, p.ej.
        ``{"2.5": {"over": 1.9, "under": 1.95}}``. Vacío si no hay mercado.
    """
    totals: dict = {}
    for bk in bookmakers or []:
        for market in bk.get("markets", []):
            if market.get("key") != "totals":
                continue
            for oc in market.get("outcomes", []):
                point = oc.get("point")
                price = oc.get("price")
                side = (oc.get("name") or "").lower()
                if point is None or not isinstance(price, (int, float)):
                    continue
                line = str(point)
                slot = "over" if side == "over" else "under" if side == "under" else None
                if slot is None:
                    continue
                bucket = totals.setdefault(line, {})
                if price > bucket.get(slot, 0.0):
                    bucket[slot] = float(price)
    return totals


def get_match_odds(home: str, away: str, league: str,
                   match_date: str | None = None) -> dict | None:
    """Busca las mejores cuotas reales para un partido.

    Args:
        home (str): Equipo local.
        away (str): Equipo visitante.
        league (str): Liga (se mapea al sport key de The Odds API).
        match_date (str | None): Fecha ISO del partido (no se usa para filtrar,
            solo informativa; el matching es por nombres de equipo).

    Returns:
        dict | None: ``{"h2h", "totals", "bookmaker_count", "commence_time"}``
        con las mejores cuotas, o None si no hay key, liga sin mapeo, o el
        partido no se encontró.
    """
    sport_key = sport_key_for(league)
    if not sport_key:
        return None

    data = _get(
        f"/sports/{sport_key}/odds",
        {"regions": REGIONS, "markets": "h2h,totals", "oddsFormat": "decimal"},
    )
    if not isinstance(data, list):
        return None

    for event in data:
        ev_home = event.get("home_team", "")
        ev_away = event.get("away_team", "")
        if _names_match(home, ev_home) and _names_match(away, ev_away):
            bookmakers = event.get("bookmakers", [])
            return {
                "h2h":             _best_h2h(bookmakers, ev_home, ev_away),
                "totals":          _best_totals(bookmakers),
                "bookmaker_count": len(bookmakers),
                "commence_time":   event.get("commence_time"),
            }
    return None


def _best_h2h_2way(bookmakers: list, home: str, away: str) -> dict | None:
    """Mejor cuota h2h a 2 vías (sin empate), para deportes tipo NBA.

    Returns:
        dict | None: ``{"home", "away"}`` con la mejor cuota, o None si falta.
    """
    best = {"home": 0.0, "away": 0.0}
    found = False
    for bk in bookmakers or []:
        for market in bk.get("markets", []):
            if market.get("key") != "h2h":
                continue
            for oc in market.get("outcomes", []):
                price = oc.get("price")
                if not isinstance(price, (int, float)):
                    continue
                if _names_match(home, oc.get("name", "")):
                    slot = "home"
                elif _names_match(away, oc.get("name", "")):
                    slot = "away"
                else:
                    continue
                if price > best[slot]:
                    best[slot] = float(price)
                    found = True
    return best if found and all(best.values()) else None


def get_nba_odds(home: str, away: str) -> dict | None:
    """Mejores cuotas reales de un partido NBA (h2h 2 vías + totales).

    Args:
        home (str): Equipo local.
        away (str): Equipo visitante.

    Returns:
        dict | None: ``{"h2h", "totals", "bookmaker_count", "commence_time"}`` o
        None si no hay key, fuera de temporada, o no se encuentra el partido.
    """
    data = _get(
        "/sports/basketball_nba/odds",
        {"regions": REGIONS, "markets": "h2h,totals", "oddsFormat": "decimal"},
    )
    if not isinstance(data, list):
        return None
    for event in data:
        ev_home = event.get("home_team", "")
        ev_away = event.get("away_team", "")
        if _names_match(home, ev_home) and _names_match(away, ev_away):
            bookmakers = event.get("bookmakers", [])
            return {
                "h2h":             _best_h2h_2way(bookmakers, ev_home, ev_away),
                "totals":          _best_totals(bookmakers),
                "bookmaker_count": len(bookmakers),
                "commence_time":   event.get("commence_time"),
            }
    return None


def list_nba_events() -> list[dict]:
    """Próximos partidos NBA con cuotas disponibles (para 'próximos partidos').

    Returns:
        list[dict]: ``[{"home", "away", "commence_time"}, ...]`` o vacío.
    """
    data = _get(
        "/sports/basketball_nba/odds",
        {"regions": REGIONS, "markets": "h2h", "oddsFormat": "decimal"},
    )
    if not isinstance(data, list):
        return []
    return [
        {"home": e.get("home_team", ""), "away": e.get("away_team", ""),
         "commence_time": e.get("commence_time")}
        for e in data
    ]


def annotate_markets(raw_odds: dict | None,
                     probabilities: dict,
                     poisson: dict | None) -> dict | None:
    """Combina cuotas reales con las probabilidades del modelo y calcula EV.

    Para cada mercado disponible en ``raw_odds`` produce un registro con la
    cuota real, la probabilidad del modelo, el EV y un flag de si hay valor.

    Args:
        raw_odds (dict | None): Salida de ``get_match_odds``.
        probabilities (dict): ``{"home_win", "draw", "away_win"}`` en %.
        poisson (dict | None): Bloque Poisson de la predicción (para over/under).

    Returns:
        dict | None: ``{"markets": {key: {...}}, "best_value": [...], ...}`` o
        None si no había cuotas.
    """
    if not raw_odds:
        return None

    markets: dict = {}

    def add(key: str, prob_pct: float | None, odds: float | None):
        if prob_pct is None or not odds:
            return
        ev = expected_value(prob_pct, odds)
        markets[key] = {
            "odds":  round(float(odds), 2),
            "prob":  round(float(prob_pct), 1),
            "ev":    ev,
            "value": ev > 0,
        }

    # ── 1X2 ──────────────────────────────────────────────────────────────
    h2h = raw_odds.get("h2h") or {}
    add("1", probabilities.get("home_win"), h2h.get("home"))
    add("X", probabilities.get("draw"),     h2h.get("draw"))
    add("2", probabilities.get("away_win"), h2h.get("away"))

    # ── Over/Under goles (las líneas que el modelo Poisson estima) ───────
    ou_model = ((poisson or {}).get("over_under") or {})
    for line, sides in (raw_odds.get("totals") or {}).items():
        p_over = ou_model.get(f"over_{line}")
        p_under = ou_model.get(f"under_{line}")
        add(f"over_{line}",  p_over,  sides.get("over"))
        add(f"under_{line}", p_under, sides.get("under"))

    best_value = sorted(
        ({"market": k, **v} for k, v in markets.items() if v["value"]),
        key=lambda m: m["ev"],
        reverse=True,
    )

    return {
        "source":          "the-odds-api",
        "bookmaker_count": raw_odds.get("bookmaker_count", 0),
        "commence_time":   raw_odds.get("commence_time"),
        "markets":         markets,
        "best_value":      best_value,
    }
