"""
build_statsbomb_profiles.py
===========================
Lee statsbomb_matches.csv y construye perfiles promedio por equipo:
- corners_for, corners_against (promedio por partido)
- yellow_for, yellow_against
- fouls_for, fouls_against
- shots_for, shots_against
- xg_for, xg_against

Guarda: backend/ml/data/team_profiles_statsbomb.json
"""

import csv
import json
from pathlib import Path
from collections import defaultdict

DATA_DIR  = Path(__file__).parent / "data"
IN_FILE   = DATA_DIR / "statsbomb_matches.csv"
OUT_FILE  = DATA_DIR / "team_profiles_statsbomb.json"


def main():
    if not IN_FILE.exists():
        print(f"No existe {IN_FILE} — ejecuta collect_statsbomb.py primero")
        return

    # Acumular por equipo
    stats = defaultdict(lambda: {
        "matches": 0,
        "home_matches": 0, "away_matches": 0,
        "corners_for": 0, "corners_against": 0,
        "yellow_for": 0,  "yellow_against": 0,
        "red_for": 0,     "red_against": 0,
        "fouls_for": 0,   "fouls_against": 0,
        "shots_for": 0,   "shots_against": 0,
        "xg_for": 0.0,    "xg_against": 0.0,
        "goals_for": 0,   "goals_against": 0,
    })

    with open(IN_FILE, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    for row in rows:
        home = row["home_team"]
        away = row["away_team"]

        def i(key): return int(row.get(key, 0) or 0)
        def f(key): return float(row.get(key, 0) or 0)

        # HOME
        s = stats[home]
        s["matches"]        += 1
        s["home_matches"]   += 1
        s["corners_for"]    += i("home_corners")
        s["corners_against"]+= i("away_corners")
        s["yellow_for"]     += i("home_yellow")
        s["yellow_against"] += i("away_yellow")
        s["red_for"]        += i("home_red")
        s["red_against"]    += i("away_red")
        s["fouls_for"]      += i("home_fouls")
        s["fouls_against"]  += i("away_fouls")
        s["shots_for"]      += i("home_shots")
        s["shots_against"]  += i("away_shots")
        s["xg_for"]         += f("home_xg")
        s["xg_against"]     += f("away_xg")
        s["goals_for"]      += i("home_goals")
        s["goals_against"]  += i("away_goals")

        # AWAY
        s = stats[away]
        s["matches"]        += 1
        s["away_matches"]   += 1
        s["corners_for"]    += i("away_corners")
        s["corners_against"]+= i("home_corners")
        s["yellow_for"]     += i("away_yellow")
        s["yellow_against"] += i("home_yellow")
        s["red_for"]        += i("away_red")
        s["red_against"]    += i("home_red")
        s["fouls_for"]      += i("away_fouls")
        s["fouls_against"]  += i("home_fouls")
        s["shots_for"]      += i("away_shots")
        s["shots_against"]  += i("home_shots")
        s["xg_for"]         += f("away_xg")
        s["xg_against"]     += f("home_xg")
        s["goals_for"]      += i("away_goals")
        s["goals_against"]  += i("home_goals")

    # Calcular promedios
    profiles = {}
    for team, s in stats.items():
        n = s["matches"]
        if n == 0:
            continue
        profiles[team] = {
            "matches": n,
            "corners_for_avg":    round(s["corners_for"]    / n, 2),
            "corners_against_avg":round(s["corners_against"]/ n, 2),
            "yellow_for_avg":     round(s["yellow_for"]     / n, 2),
            "yellow_against_avg": round(s["yellow_against"] / n, 2),
            "red_for_avg":        round(s["red_for"]        / n, 3),
            "red_against_avg":    round(s["red_against"]    / n, 3),
            "fouls_for_avg":      round(s["fouls_for"]      / n, 2),
            "fouls_against_avg":  round(s["fouls_against"]  / n, 2),
            "shots_for_avg":      round(s["shots_for"]      / n, 2),
            "shots_against_avg":  round(s["shots_against"]  / n, 2),
            "xg_for_avg":         round(s["xg_for"]         / n, 3),
            "xg_against_avg":     round(s["xg_against"]     / n, 3),
            "goals_for_avg":      round(s["goals_for"]      / n, 2),
            "goals_against_avg":  round(s["goals_against"]  / n, 2),
        }

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(profiles, f, ensure_ascii=False, indent=2)

    print(f"Perfiles guardados: {OUT_FILE}")
    print(f"Equipos: {len(profiles)}")
    print()

    # Mostrar muestra
    sample = list(profiles.items())[:5]
    for team, p in sample:
        print(f"{team} ({p['matches']} partidos):")
        print(f"  Corners: {p['corners_for_avg']} a favor / {p['corners_against_avg']} en contra")
        print(f"  Amarillas: {p['yellow_for_avg']} / Faltas: {p['fouls_for_avg']}")
        print(f"  xG: {p['xg_for_avg']} / Disparos: {p['shots_for_avg']}")
        print()

    # Globales para usar como fallback
    all_corners = sum(s["corners_for"] for s in stats.values()) / sum(s["matches"] for s in stats.values())
    all_yellow  = sum(s["yellow_for"]  for s in stats.values()) / sum(s["matches"] for s in stats.values())
    all_fouls   = sum(s["fouls_for"]   for s in stats.values()) / sum(s["matches"] for s in stats.values())
    print(f"Promedios globales por equipo por partido:")
    print(f"  Corners:   {all_corners:.2f}")
    print(f"  Amarillas: {all_yellow:.2f}")
    print(f"  Faltas:    {all_fouls:.2f}")


if __name__ == "__main__":
    main()
