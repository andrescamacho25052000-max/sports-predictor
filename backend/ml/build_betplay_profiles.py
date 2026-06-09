"""
build_betplay_profiles.py
==========================
Lee betplay_matches.csv y fusiona los perfiles de equipos colombianos
con los perfiles StatsBomb existentes en team_profiles_statsbomb.json.

Los equipos BetPlay pasan a tener datos reales en vez de usar el promedio global.
"""

import csv, json
from pathlib import Path
from collections import defaultdict

DATA_DIR       = Path(__file__).parent / "data"
BETPLAY_CSV    = DATA_DIR / "betplay_matches.csv"
STATSBOMB_JSON = DATA_DIR / "team_profiles_statsbomb.json"
OUT_JSON       = DATA_DIR / "team_profiles_statsbomb.json"  # sobreescribir con merge


def main():
    if not BETPLAY_CSV.exists():
        print("No existe betplay_matches.csv — ejecuta collect_betplay_stats.py primero")
        return

    # Cargar perfiles existentes
    profiles = {}
    if STATSBOMB_JSON.exists():
        with open(STATSBOMB_JSON, encoding="utf-8") as f:
            profiles = json.load(f)
    print(f"Perfiles existentes (StatsBomb): {len(profiles)}")

    # Acumular stats BetPlay por equipo
    stats = defaultdict(lambda: {
        "matches": 0,
        "corners_for": 0, "corners_against": 0,
        "yellow_for": 0,  "yellow_against": 0,
        "red_for": 0,     "red_against": 0,
        "fouls_for": 0,   "fouls_against": 0,
        "shots_for": 0,   "shots_against": 0,
        "goals_for": 0,   "goals_against": 0,
    })

    with open(BETPLAY_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Partidos BetPlay con estadísticas: {len(rows)}")

    def iv(row, key, default=0):
        try:
            return int(float(row.get(key) or default))
        except:
            return default

    for row in rows:
        home = row["home_team"]
        away = row["away_team"]

        # HOME
        s = stats[home]
        s["matches"]         += 1
        s["corners_for"]     += iv(row, "home_corners")
        s["corners_against"] += iv(row, "away_corners")
        s["yellow_for"]      += iv(row, "home_yellow")
        s["yellow_against"]  += iv(row, "away_yellow")
        s["red_for"]         += iv(row, "home_red")
        s["red_against"]     += iv(row, "away_red")
        s["fouls_for"]       += iv(row, "home_fouls")
        s["fouls_against"]   += iv(row, "away_fouls")
        s["shots_for"]       += iv(row, "home_shots")
        s["shots_against"]   += iv(row, "away_shots")
        s["goals_for"]       += iv(row, "home_goals")
        s["goals_against"]   += iv(row, "away_goals")

        # AWAY
        s = stats[away]
        s["matches"]         += 1
        s["corners_for"]     += iv(row, "away_corners")
        s["corners_against"] += iv(row, "home_corners")
        s["yellow_for"]      += iv(row, "away_yellow")
        s["yellow_against"]  += iv(row, "home_yellow")
        s["red_for"]         += iv(row, "away_red")
        s["red_against"]     += iv(row, "home_red")
        s["fouls_for"]       += iv(row, "away_fouls")
        s["fouls_against"]   += iv(row, "home_fouls")
        s["shots_for"]       += iv(row, "away_shots")
        s["shots_against"]   += iv(row, "home_shots")
        s["goals_for"]       += iv(row, "away_goals")
        s["goals_against"]   += iv(row, "home_goals")

    # Fusionar con perfiles existentes (BetPlay sobreescribe/agrega)
    new_teams = 0
    updated_teams = 0
    for team, s in stats.items():
        n = s["matches"]
        if n == 0:
            continue
        new_profile = {
            "matches":             n,
            "corners_for_avg":     round(s["corners_for"]    / n, 2),
            "corners_against_avg": round(s["corners_against"]/ n, 2),
            "yellow_for_avg":      round(s["yellow_for"]     / n, 2),
            "yellow_against_avg":  round(s["yellow_against"] / n, 2),
            "red_for_avg":         round(s["red_for"]        / n, 3),
            "red_against_avg":     round(s["red_against"]    / n, 3),
            "fouls_for_avg":       round(s["fouls_for"]      / n, 2),
            "fouls_against_avg":   round(s["fouls_against"]  / n, 2),
            "shots_for_avg":       round(s["shots_for"]      / n, 2),
            "shots_against_avg":   round(s["shots_against"]  / n, 2),
            "xg_for_avg":          0.0,   # no disponible en API-Sports free
            "xg_against_avg":      0.0,
            "goals_for_avg":       round(s["goals_for"]      / n, 2),
            "goals_against_avg":   round(s["goals_against"]  / n, 2),
            "source":              "betplay_api",
        }
        if team in profiles:
            updated_teams += 1
        else:
            new_teams += 1
        profiles[team] = new_profile

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(profiles, f, ensure_ascii=False, indent=2)

    print(f"\nPerfiles actualizados: {OUT_JSON}")
    print(f"  Equipos nuevos (BetPlay): {new_teams}")
    print(f"  Equipos actualizados:     {updated_teams}")
    print(f"  Total en perfiles:        {len(profiles)}")
    print()

    # Mostrar muestra de equipos colombianos
    col_teams = [t for t in stats.keys()][:6]
    for team in col_teams:
        p = profiles[team]
        print(f"{team} ({p['matches']} partidos):")
        print(f"  Corners:   {p['corners_for_avg']:.1f} a favor / {p['corners_against_avg']:.1f} en contra")
        print(f"  Amarillas: {p['yellow_for_avg']:.1f} | Faltas: {p['fouls_for_avg']:.1f}")


if __name__ == "__main__":
    main()
