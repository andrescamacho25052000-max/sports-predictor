"""
ml/ingest_clubs.py — Partidos de clubes (con cuotas) -> scouting_matches.

Fuente: espejo GitHub de football-data.co.uk (no bloqueado). Carga resultados y
las cuotas 1X2 promedio de las principales ligas de clubes, en scouting_matches
con competition_type='club'. Las cuotas van compactas en `raw` para no ocupar
mucho (plan gratuito de Supabase).

Uso:  python -m ml.ingest_clubs
"""
import csv
import io
from datetime import datetime

import requests

import supabase_client as sbc

BASE = "https://raw.githubusercontent.com/huhao930422-debug/football-odds-mirror/master/data"
API = "https://api.github.com/repos/huhao930422-debug/football-odds-mirror/contents/data"
UA = {"User-Agent": "Mozilla/5.0"}

# Liga (carpeta del espejo) -> nombre legible
LEAGUES = {
    "premier-league": "Premier League", "la-liga": "La Liga",
    "bundesliga": "Bundesliga", "serie-a": "Serie A", "ligue-1": "Ligue 1",
    "championship": "Championship", "eredivisie": "Eredivisie",
    "primeira-liga": "Primeira Liga", "serie-b": "Serie B",
    "la-liga-2": "La Liga 2", "bundesliga-2": "Bundesliga 2", "ligue-2": "Ligue 2",
    "scottish-premiership": "Scottish Premiership", "super-lig": "Super Lig",
    "jupiler-league": "Jupiler League",
}


def _iso(d):
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(d.strip(), fmt).strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            continue
    return None


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _int(v):
    v = (v or "").strip()
    return int(v) if v.lstrip("-").isdigit() else None


def _season_files(folder):
    r = requests.get(f"{API}/{folder}", timeout=30, headers=UA)
    if r.status_code != 200:
        return []
    return [it["name"] for it in r.json()
            if it["name"].startswith("season-") and it["name"].endswith(".csv")]


def _batches(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def run():
    sb = sbc.get_client()
    if not sb:
        print("ERROR: sin cliente Supabase."); return

    all_matches, teams = [], set()
    for folder, league in LEAGUES.items():
        files = _season_files(folder)
        n_league = 0
        for fname in files:
            try:
                r = requests.get(f"{BASE}/{folder}/{fname}", timeout=30, headers=UA)
                if r.status_code != 200:
                    continue
            except Exception:
                continue
            for row in csv.DictReader(io.StringIO(r.text)):
                date = _iso(row.get("Date"))
                home = (row.get("HomeTeam") or "").strip()
                away = (row.get("AwayTeam") or "").strip()
                hg, ag = _int(row.get("FTHG")), _int(row.get("FTAG"))
                if not (date and home and away and hg is not None and ag is not None):
                    continue
                oh = _f(row.get("AvgH")) or _f(row.get("B365H"))
                od = _f(row.get("AvgD")) or _f(row.get("B365D"))
                oa = _f(row.get("AvgA")) or _f(row.get("B365A"))
                teams.add(home); teams.add(away)
                all_matches.append({
                    "source": "football-data.co.uk (mirror)",
                    "competition_type": "club", "category": "liga",
                    "tournament": league, "match_date": date,
                    "home_team": home, "away_team": away,
                    "home_goals": hg, "away_goals": ag,
                    "winner": "Local" if hg > ag else "Visitante" if ag > hg else "Empate",
                    "ht_home_goals": _int(row.get("HTHG")), "ht_away_goals": _int(row.get("HTAG")),
                    "raw": {"odds": {"h": oh, "d": od, "a": oa}} if (oh and od and oa) else None,
                })
                n_league += 1
        print(f"{league}: {n_league} partidos")

    print(f"TOTAL clubes: {len(all_matches)} | equipos: {len(teams)}")

    # Equipos (upsert por nombre)
    for b in _batches([{"name": t, "type": "club"} for t in sorted(teams)], 500):
        sb.table("scouting_teams").upsert(b, on_conflict="name").execute()

    name_to_id, off = {}, 0
    while True:
        res = sb.table("scouting_teams").select("id,name").range(off, off + 999).execute()
        data = res.data or []
        for row in data:
            name_to_id[row["name"]] = row["id"]
        if len(data) < 1000:
            break
        off += 1000

    # Deduplicar por clave unica y resolver team_ids
    seen, uniq = set(), []
    for m in all_matches:
        key = (m["tournament"], m["match_date"], m["home_team"], m["away_team"])
        if key in seen:
            continue
        seen.add(key)
        m["home_team_id"] = name_to_id.get(m["home_team"])
        m["away_team_id"] = name_to_id.get(m["away_team"])
        uniq.append(m)

    total = 0
    for b in _batches(uniq, 1000):
        sb.table("scouting_matches").upsert(
            b, on_conflict="tournament,match_date,home_team,away_team").execute()
        total += len(b)
        print(f"  ... {total}/{len(uniq)}")
    print(f"Listo. {total} partidos de clubes cargados.")


if __name__ == "__main__":
    run()
