"""
collect_statsbomb.py
====================
Descarga datos de StatsBomb Open Data (GitHub) y extrae estadísticas
por partido: córners, tarjetas, faltas, disparos, xG.

Guarda: backend/ml/data/statsbomb_matches.csv
"""

import json
import time
import urllib.request
from pathlib import Path

BASE = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"

# Competiciones a descargar (competition_id, season_id, nombre legible)
COMPETITIONS = [
    (43, 106, "World Cup 2022"),
    (43,   3, "World Cup 2018"),
    (55, 282, "Euro 2024"),
    (55,  43, "Euro 2020"),
    (223,282, "Copa America 2024"),
    (11,  90, "La Liga 2020/21"),
    (11,  42, "La Liga 2019/20"),
    (11,   4, "La Liga 2018/19"),
    (2,   27, "Premier League 2015/16"),
    (9,  281, "Bundesliga 2023/24"),
    (7,  235, "Ligue 1 2022/23"),
    (12,  27, "Serie A 2015/16"),
    (1267,107,"AFCON 2023"),
]

OUT_DIR  = Path(__file__).parent / "data"
OUT_FILE = OUT_DIR / "statsbomb_matches.csv"
OUT_DIR.mkdir(exist_ok=True)


def fetch(url: str, retries: int = 3) -> dict | list | None:
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=15) as r:
                return json.loads(r.read())
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1)
            else:
                print(f"  ERROR fetching {url}: {e}")
                return None


def extract_match_stats(events: list, home_id: int, away_id: int) -> dict:
    """Extrae stats agregadas de la lista de eventos de un partido."""
    stats = {
        "home_corners": 0, "away_corners": 0,
        "home_yellow":  0, "away_yellow":  0,
        "home_red":     0, "away_red":     0,
        "home_fouls":   0, "away_fouls":   0,
        "home_shots":   0, "away_shots":   0,
        "home_shots_ot":0, "away_shots_ot":0,
        "home_xg":    0.0, "away_xg":    0.0,
    }

    for ev in events:
        t = ev.get("type", {}).get("name", "")
        team_id = ev.get("team", {}).get("id")
        is_home = (team_id == home_id)
        prefix  = "home" if is_home else "away"

        # Corners
        if t == "Pass":
            ptype = ev.get("pass", {}).get("type", {}).get("name", "")
            if ptype == "Corner":
                stats[f"{prefix}_corners"] += 1

        # Tarjetas (en Foul Committed)
        elif t == "Foul Committed":
            stats[f"{prefix}_fouls"] += 1
            card = ev.get("foul_committed", {}).get("card", {}).get("name", "")
            if "Yellow" in card:
                stats[f"{prefix}_yellow"] += 1
            elif "Red" in card:
                stats[f"{prefix}_red"] += 1

        # Disparos
        elif t == "Shot":
            shot = ev.get("shot", {})
            stats[f"{prefix}_shots"] += 1
            outcome = shot.get("outcome", {}).get("name", "")
            if outcome in ("Goal", "Saved", "Saved To Post"):
                stats[f"{prefix}_shots_ot"] += 1
            xg = shot.get("statsbomb_xg", 0) or 0
            stats[f"{prefix}_xg"] += xg

        # Own goals cuentan como xG del rival
        elif t in ("Own Goal For", "Own Goal Against"):
            pass  # no tienen xG, ignoramos

    return stats


def main():
    rows = []

    for comp_id, season_id, comp_name in COMPETITIONS:
        matches_url = f"{BASE}/matches/{comp_id}/{season_id}.json"
        matches = fetch(matches_url)
        if not matches:
            continue

        print(f"\n{comp_name}: {len(matches)} partidos")

        for i, m in enumerate(matches):
            match_id  = m["match_id"]
            home_name = m["home_team"]["home_team_name"]
            away_name = m["away_team"]["away_team_name"]
            home_id   = m["home_team"]["home_team_id"]
            away_id   = m["away_team"]["away_team_id"]
            home_score= m["home_score"]
            away_score= m["away_score"]
            date      = m["match_date"]

            # Descargar eventos
            events_url = f"{BASE}/events/{match_id}.json"
            events = fetch(events_url)
            if not events:
                print(f"  [{i+1}/{len(matches)}] {home_name} vs {away_name} — sin eventos")
                continue

            stats = extract_match_stats(events, home_id, away_id)

            row = {
                "match_id":    match_id,
                "competition": comp_name,
                "date":        date,
                "home_team":   home_name,
                "away_team":   away_name,
                "home_id":     home_id,
                "away_id":     away_id,
                "home_goals":  home_score,
                "away_goals":  away_score,
                **stats,
            }
            rows.append(row)
            print(f"  [{i+1}/{len(matches)}] {home_name} {home_score}-{away_score} {away_name} "
                  f"| corners {stats['home_corners']}-{stats['away_corners']} "
                  f"| yellows {stats['home_yellow']}-{stats['away_yellow']} "
                  f"| xG {stats['home_xg']:.2f}-{stats['away_xg']:.2f}")

            time.sleep(0.05)  # respetuoso con GitHub

    # Guardar CSV
    if not rows:
        print("Sin datos, abortando.")
        return

    import csv
    fieldnames = list(rows[0].keys())
    with open(OUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nGuardado: {OUT_FILE}")
    print(f"Total partidos procesados: {len(rows)}")


if __name__ == "__main__":
    main()
