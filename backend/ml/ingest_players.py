"""
ml/ingest_players.py — Tarjeta de jugador (v1: goleadores) -> scouting_players.

Agrega los 47.8k goles internacionales por jugador para armar una "tarjeta" con:
seleccion, goles de carrera, penales, autogoles, partidos en que marco y años
activos. Fuente: goalscorers.csv (martj42). Es la primera capa; luego se enriquece
con StatsBomb (stats por partido) y API-Sports (edad, club, historial).

Uso:
    python -m ml.ingest_players --dry-run   # valida y muestra el top, sin base
    python -m ml.ingest_players             # carga a scouting_players
"""
import csv
import io
import sys
from collections import defaultdict, Counter

try:  # evitar UnicodeEncodeError en la consola de Windows (nombres con acentos)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import requests

import supabase_client as sbc

URL = "https://raw.githubusercontent.com/martj42/international_results/master/goalscorers.csv"
UA = {"User-Agent": "Mozilla/5.0"}


def aggregate():
    """Devuelve {nombre: {stats...}} agregando todos los goles por jugador."""
    r = requests.get(URL, timeout=60, headers=UA)
    r.encoding = "utf-8"
    goals = list(csv.DictReader(io.StringIO(r.text)))

    acc = defaultdict(lambda: {
        "goals": 0, "penalties": 0, "own_goals": 0,
        "teams": Counter(), "matches": set(), "years": [],
    })
    for g in goals:
        scorer = (g.get("scorer") or "").strip()
        if not scorer:
            continue
        team = (g.get("team") or "").strip()
        year = (g.get("date") or "")[:4]
        own = g.get("own_goal", "").strip().upper() == "TRUE"
        pen = g.get("penalty", "").strip().upper() == "TRUE"
        a = acc[scorer]
        if own:
            a["own_goals"] += 1
        else:
            a["goals"] += 1
            if pen:
                a["penalties"] += 1
            a["teams"][team] += 1   # su seleccion (solo goles validos)
        a["matches"].add((g.get("date"), g.get("home_team"), g.get("away_team")))
        if year.isdigit():
            a["years"].append(int(year))

    players = {}
    for name, a in acc.items():
        nat = a["teams"].most_common(1)[0][0] if a["teams"] else None
        players[name] = {
            "national_team": nat,
            "goals": a["goals"], "penalties": a["penalties"], "own_goals": a["own_goals"],
            "matches_scored": len(a["matches"]),
            "first_year": min(a["years"]) if a["years"] else None,
            "last_year": max(a["years"]) if a["years"] else None,
        }
    return players


def _batches(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def run(dry_run=False):
    players = aggregate()
    print(f"Jugadores (goleadores) distintos: {len(players)}")

    top = sorted(players.items(), key=lambda kv: kv[1]["goals"], reverse=True)[:12]
    print("\nTop goleadores internacionales de la historia:")
    for name, s in top:
        print(f"  {s['goals']:3d} goles  {name} ({s['national_team']}) "
              f"| {s['penalties']} penales | {s['first_year']}-{s['last_year']}")

    if dry_run:
        print("\n[DRY-RUN] No se inserto nada.")
        return

    sb = sbc.get_client()
    if not sb:
        print("ERROR: sin cliente Supabase."); return

    rows = []
    for name, s in players.items():
        rows.append({
            "name": name,
            "nationality": s["national_team"],
            "national_team": s["national_team"],
            "career_stats": {
                "goals": s["goals"], "penalties": s["penalties"], "own_goals": s["own_goals"],
                "matches_scored": s["matches_scored"],
                "first_year": s["first_year"], "last_year": s["last_year"],
                "source": "international_goals",
            },
        })
    total = 0
    for b in _batches(rows, 500):
        sb.table("scouting_players").upsert(b, on_conflict="name").execute()
        total += len(b)
        print(f"  ... {total}/{len(rows)}")
    print(f"Listo. {total} jugadores en scouting_players.")


if __name__ == "__main__":
    run(dry_run="--dry-run" in sys.argv)
