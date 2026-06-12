"""
build_national_elo.py — Calcula Elo y forma reciente de selecciones nacionales
a partir del dataset abierto de resultados internacionales (martj42, 49k partidos
desde 1872) y los integra al sistema:

  1. Elo de selecciones -> se MEZCLA en ml/data/elo_ratings.json (mismo formato
     team_id -> rating que ya usa ml_predictor; cero cambios de código allí).
  2. Forma reciente (últimos 5 jugados) -> ml/data/national_form.json, usado por
     football_api.get_team_form como fallback cuando la API no tiene partidos.

El mapeo nombre -> ID se hace contra los equipos del Mundial en football-data.org.

Uso:  python ml/build_national_elo.py   (desde backend/)
"""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import requests

DATA_DIR  = os.path.join(os.path.dirname(__file__), "data")
CSV_PATH  = os.path.join(DATA_DIR, "international_results.csv")
ELO_PATH  = os.path.join(DATA_DIR, "elo_ratings.json")
FORM_PATH = os.path.join(DATA_DIR, "national_form.json")

CSV_URL = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"


def download_csv() -> bool:
    """Descarga la versión más reciente del dataset (se actualiza a diario)."""
    try:
        r = requests.get(CSV_URL, timeout=60)
        r.raise_for_status()
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(CSV_PATH, "wb") as f:
            f.write(r.content)
        print(f"[NationalElo] CSV descargado ({len(r.content)//1024} KB)")
        return True
    except Exception as e:
        print(f"[NationalElo] No se pudo descargar el CSV: {e}")
        return False

BASE_ELO = 1500.0
HOME_ADV = 100.0

# football-data.org -> nombre en el dataset (solo donde difieren)
FD_TO_DATASET = {
    "Czechia":            "Czech Republic",
    "Bosnia-Herzegovina": "Bosnia and Herzegovina",
    "Cape Verde Islands": "Cape Verde",
    "Congo DR":           "DR Congo",
}


def k_factor(tournament: str) -> float:
    t = tournament.lower()
    if t == "friendly":
        return 20
    if "fifa world cup" in t:
        return 40 if "qualification" in t else 60
    if "qualification" in t:
        return 40
    if any(x in t for x in (
        "uefa euro", "copa américa", "copa america", "african cup",
        "africa cup", "asian cup", "gold cup", "concacaf championship",
        "confederations cup",
    )):
        return 50
    if "nations league" in t:
        return 40
    return 30


def goal_mult(diff: int) -> float:
    diff = abs(diff)
    if diff <= 1:
        return 1.0
    if diff == 2:
        return 1.5
    return 1.75 + (diff - 3) / 8


def parse_score(s: str) -> int | None:
    try:
        return int(s)
    except (ValueError, TypeError):
        return None


def rebuild(download: bool = True) -> dict:
    """
    Punto de entrada para el backend: descarga el CSV actualizado (opcional),
    recalcula Elo + forma y escribe los JSON. Devuelve un resumen.
    """
    if download:
        download_csv()
    if not os.path.exists(CSV_PATH):
        return {"error": "CSV no disponible y no se pudo descargar"}
    return main()


def main():
    # ── 1. Calcular Elo + historial por selección ─────────────────────────
    ratings: dict[str, float] = {}
    history: dict[str, list] = {}   # nombre -> partidos jugados (cronológico)

    rows = []
    with open(CSV_PATH, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            h, a = parse_score(row["home_score"]), parse_score(row["away_score"])
            if h is None or a is None:
                continue  # partido futuro / sin datos
            rows.append((row["date"], row["home_team"], row["away_team"], h, a,
                         row["tournament"], row["neutral"].strip().upper() == "TRUE"))

    rows.sort(key=lambda r: r[0])
    print(f"Partidos con resultado: {len(rows)} ({rows[0][0]} -> {rows[-1][0]})")

    for date, home, away, hg, ag, tournament, neutral in rows:
        ra = ratings.get(home, BASE_ELO)
        rb = ratings.get(away, BASE_ELO)
        adv = 0.0 if neutral else HOME_ADV

        we_home = 1 / (1 + 10 ** ((rb - ra - adv) / 400))
        w_home  = 1.0 if hg > ag else 0.5 if hg == ag else 0.0

        delta = k_factor(tournament) * goal_mult(hg - ag) * (w_home - we_home)
        ratings[home] = ra + delta
        ratings[away] = rb - delta

        history.setdefault(home, []).append(
            {"date": date, "opponent": away, "gf": hg, "gc": ag,
             "was_home": not neutral})
        history.setdefault(away, []).append(
            {"date": date, "opponent": home, "gf": ag, "gc": hg,
             "was_home": False})

    # ── 2. Equipos del Mundial: id -> nombre desde football-data.org ─────
    # Si la API falla (rate limit 429, red), reusar el mapeo del archivo
    # anterior: los IDs de las 48 selecciones no cambian durante el torneo.
    fd_teams: dict[int, str] = {}
    try:
        r = requests.get(
            "https://api.football-data.org/v4/competitions/WC/matches",
            headers={"X-Auth-Token": os.getenv("FOOTBALL_API_KEY")}, timeout=20)
        r.raise_for_status()
        for m in r.json().get("matches", []):
            for side in ("homeTeam", "awayTeam"):
                t = m.get(side, {})
                if t.get("id") and t.get("name"):
                    fd_teams[t["id"]] = t["name"]
        print(f"Equipos del Mundial en football-data.org: {len(fd_teams)}")
    except Exception as e:
        print(f"[NationalElo] API no disponible ({e}); usando mapeo previo")
        try:
            with open(FORM_PATH, encoding="utf-8") as f:
                fd_teams = {int(k): v["name"] for k, v in json.load(f).items()}
        except Exception:
            return {"error": "Sin API ni mapeo previo de equipos — reintentar luego"}

    # ── 3. Mapear y generar salidas ───────────────────────────────────────
    # En producción elo_ratings.json puede no existir (está gitignorado);
    # se parte de cero y solo contendrá selecciones.
    try:
        with open(ELO_PATH, encoding="utf-8") as f:
            elo_out = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        elo_out = {}
    club_keys = set(elo_out.keys())

    form_out: dict[str, dict] = {}
    unmatched = []

    for fd_id, fd_name in sorted(fd_teams.items(), key=lambda x: x[1]):
        ds_name = FD_TO_DATASET.get(fd_name, fd_name)
        if ds_name not in ratings:
            unmatched.append(fd_name)
            continue

        if str(fd_id) in club_keys:
            print(f"  AVISO: id {fd_id} ({fd_name}) ya existia en elo_ratings.json — se sobreescribe")
        elo_out[str(fd_id)] = round(ratings[ds_name], 1)

        last5  = history[ds_name][-5:]
        last10 = history[ds_name][-10:]
        wins   = sum(1 for m in last5 if m["gf"] > m["gc"])
        draws  = sum(1 for m in last5 if m["gf"] == m["gc"])
        pts10  = sum(3 if m["gf"] > m["gc"] else 1 if m["gf"] == m["gc"] else 0
                     for m in last10)

        form_out[str(fd_id)] = {
            "name":                 fd_name,
            "wins_last5":           wins,
            "draws_last5":          draws,
            "losses_last5":         len(last5) - wins - draws,
            "goals_scored_last5":   sum(m["gf"] for m in last5),
            "goals_conceded_last5": sum(m["gc"] for m in last5),
            "possession_avg":       50,
            "shots_on_target_avg":  5.0,
            "injured_players":      0,
            "yellow_cards_last5":   0,
            "red_cards_last5":      0,
            "ranking":              10,
            "played":               len(last5),
            "pts_per_game":         round(pts10 / max(len(last10), 1), 2),
            "elo":                  round(ratings[ds_name], 1),
            "recent_matches": [
                {"opponent": m["opponent"], "goals_for": m["gf"],
                 "goals_against": m["gc"],
                 "result": "V" if m["gf"] > m["gc"] else "E" if m["gf"] == m["gc"] else "D",
                 "was_home": m["was_home"], "date": m["date"]}
                for m in last5
            ],
        }

    with open(ELO_PATH, "w", encoding="utf-8") as f:
        json.dump(elo_out, f, ensure_ascii=False, indent=1)
    with open(FORM_PATH, "w", encoding="utf-8") as f:
        json.dump(form_out, f, ensure_ascii=False, indent=1)

    print(f"\nElo total en archivo: {len(elo_out)} equipos "
          f"({len(elo_out) - len(club_keys)} selecciones agregadas)")
    print(f"Forma guardada para {len(form_out)} selecciones")
    if unmatched:
        print(f"SIN MAPEAR ({len(unmatched)}): {unmatched}")

    print("\nTop 15 Elo de selecciones del Mundial:")
    ranked = sorted(form_out.values(), key=lambda x: -x["elo"])
    for i, t in enumerate(ranked[:15], 1):
        print(f"  {i:2}. {t['name']:22} {t['elo']:7.1f}  "
              f"({t['wins_last5']}V/{t['draws_last5']}E/{t['losses_last5']}D)")

    return {
        "matches_processed": len(rows),
        "last_match_date":   rows[-1][0] if rows else None,
        "teams_mapped":      len(form_out),
        "unmatched":         unmatched,
    }


if __name__ == "__main__":
    main()
