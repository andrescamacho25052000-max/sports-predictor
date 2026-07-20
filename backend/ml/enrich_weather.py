"""
ml/enrich_weather.py — Clima historico para scouting_matches (Open-Meteo archive).

Rellena temp_c, feels_like_c (sensacion termica), precip_mm, wind_kmh y weather_desc
de cada partido, geocodificando la ciudad. Solo hay datos desde 1940.

Es RESUMIBLE (solo procesa partidos sin clima) y se corre POR TANDAS/PRIORIDAD para
respetar los limites de la API. El clima es un predictor debil, asi que conviene
enriquecer primero los partidos que de verdad se van a modelar (Mundiales, etc.).

Uso:
    python -m ml.enrich_weather --category mundial
    python -m ml.enrich_weather --limit 1000
"""
import json
import os
import sys
import time

import requests

import supabase_client as sbc

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CACHE_PATH = os.path.join(DATA_DIR, "geocode_cache.json")
UA = {"User-Agent": "Mozilla/5.0"}
GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# Codigos WMO -> descripcion corta
WMO = {
    0: "Despejado", 1: "Mayormente despejado", 2: "Parcialmente nublado", 3: "Nublado",
    45: "Niebla", 48: "Niebla", 51: "Llovizna", 53: "Llovizna", 55: "Llovizna",
    61: "Lluvia ligera", 63: "Lluvia", 65: "Lluvia fuerte", 71: "Nieve", 73: "Nieve",
    75: "Nieve fuerte", 80: "Chubascos", 81: "Chubascos", 82: "Chubascos fuertes",
    95: "Tormenta", 96: "Tormenta", 99: "Tormenta",
}


def _load_cache() -> dict:
    if os.path.exists(CACHE_PATH):
        try:
            return json.loads(open(CACHE_PATH, encoding="utf-8").read())
        except Exception:
            pass
    return {}


def _save_cache(cache: dict):
    open(CACHE_PATH, "w", encoding="utf-8").write(json.dumps(cache, ensure_ascii=False))


def _geocode(city: str, country: str, cache: dict):
    key = f"{city}|{country}"
    if key in cache:
        return cache[key]
    try:
        r = requests.get(GEO_URL, params={"name": city, "count": 1}, timeout=15, headers=UA)
        res = (r.json().get("results") or [None])[0]
        loc = [res["latitude"], res["longitude"]] if res else None
    except Exception:
        loc = None
    cache[key] = loc
    return loc


def _weather(lat, lon, date):
    try:
        r = requests.get(ARCHIVE_URL, params={
            "latitude": lat, "longitude": lon, "start_date": date, "end_date": date,
            "daily": "temperature_2m_max,temperature_2m_min,apparent_temperature_max,"
                     "precipitation_sum,wind_speed_10m_max,weather_code",
            "timezone": "auto",
        }, timeout=20, headers=UA)
        d = r.json().get("daily", {})
        def first(k):
            v = d.get(k) or [None]
            return v[0]
        code = first("weather_code")
        return {
            "temp_c":       first("temperature_2m_max"),
            "feels_like_c": first("apparent_temperature_max"),
            "precip_mm":    first("precipitation_sum"),
            "wind_kmh":     first("wind_speed_10m_max"),
            "weather_desc": WMO.get(int(code), None) if code is not None else None,
        }
    except Exception:
        return None


def run(category: str | None = None, limit: int = 1200):
    sb = sbc.get_client()
    if not sb:
        print("ERROR: sin cliente Supabase.")
        return

    q = (sb.table("scouting_matches")
           .select("id,match_date,city,country")
           .is_("temp_c", "null")
           .gte("match_date", "1940-01-01")
           .not_.is_("city", "null"))
    if category:
        q = q.eq("category", category)
    rows = q.order("match_date", desc=True).limit(limit).execute().data or []
    print(f"Partidos por enriquecer: {len(rows)}" + (f" (categoria {category})" if category else ""))

    cache = _load_cache()
    done = skipped = 0
    for i, m in enumerate(rows, 1):
        loc = _geocode(m["city"], m.get("country") or "", cache)
        if not loc:
            skipped += 1
            continue
        w = _weather(loc[0], loc[1], m["match_date"])
        if not w or w["temp_c"] is None:
            skipped += 1
            continue
        sb.table("scouting_matches").update(w).eq("id", m["id"]).execute()
        done += 1
        if i % 50 == 0:
            _save_cache(cache)
            print(f"  ... {i}/{len(rows)} (ok {done}, sin dato {skipped})")
        time.sleep(0.15)

    _save_cache(cache)
    print(f"Listo. Enriquecidos {done}, sin dato {skipped}.")


if __name__ == "__main__":
    args = sys.argv[1:]
    cat = None
    lim = 1200
    if "--category" in args:
        cat = args[args.index("--category") + 1]
    if "--limit" in args:
        lim = int(args[args.index("--limit") + 1])
    run(category=cat, limit=lim)
