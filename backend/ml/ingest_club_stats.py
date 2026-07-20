"""
ml/ingest_club_stats.py — Stats de clubes (tiros, corners, tarjetas, faltas)
-> scouting_match_team_stats.

Fuente: los mismos CSV del espejo football-data.co.uk (columnas HS/AS, HST/AST,
HC/AC, HF/AF, HY/AY, HR/AR). NO tiene xG (eso se saca de understat aparte).
Cruza con los partidos de clubes ya cargados en scouting_matches por
(tournament, fecha, local, visitante). Procesa liga por liga.

Uso:  python -m ml.ingest_club_stats
"""
import csv
import io
from datetime import datetime

import requests

import supabase_client as sbc

BASE = "https://raw.githubusercontent.com/huhao930422-debug/football-odds-mirror/master/data"
API = "https://api.github.com/repos/huhao930422-debug/football-odds-mirror/contents/data"
UA = {"User-Agent": "Mozilla/5.0"}

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
            return datetime.strptime((d or "").strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _int(v):
    v = (v or "").strip()
    return int(float(v)) if v.replace(".", "").lstrip("-").isdigit() else None


def _season_files(folder):
    r = requests.get(f"{API}/{folder}", timeout=30, headers=UA)
    if r.status_code != 200:
        return []
    return [it["name"] for it in r.json()
            if it["name"].startswith("season-") and it["name"].endswith(".csv")]


def _index_league(sb, league):
    """(fecha, local, visitante) -> {id, hid, aid} para los partidos de esa liga."""
    idx, off = {}, 0
    while True:
        res = (sb.table("scouting_matches")
                 .select("id,match_date,home_team,away_team,home_team_id,away_team_id")
                 .eq("competition_type", "club").eq("tournament", league)
                 .range(off, off + 999).execute())
        data = res.data or []
        for m in data:
            idx[(m["match_date"], m["home_team"], m["away_team"])] = m
        if len(data) < 1000:
            break
        off += 1000
    return idx


def _batches(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def run():
    sb = sbc.get_client()
    if not sb:
        print("ERROR: sin cliente Supabase."); return

    grand = 0
    for folder, league in LEAGUES.items():
        idx = _index_league(sb, league)
        rows = []
        for fname in _season_files(folder):
            try:
                r = requests.get(f"{BASE}/{folder}/{fname}", timeout=30, headers=UA)
                if r.status_code != 200:
                    continue
            except Exception:
                continue
            for row in csv.DictReader(io.StringIO(r.text)):
                hs, as_ = _int(row.get("HS")), _int(row.get("AS"))
                hc, ac = _int(row.get("HC")), _int(row.get("AC"))
                hy, ay = _int(row.get("HY")), _int(row.get("AY"))
                if hs is None and hc is None and hy is None:
                    continue  # sin stats en esa temporada
                key = (_iso(row.get("Date")), (row.get("HomeTeam") or "").strip(),
                       (row.get("AwayTeam") or "").strip())
                m = idx.get(key)
                if not m:
                    continue
                rows.append({
                    "match_id": m["id"], "team_id": m["home_team_id"], "is_home": True,
                    "shots": hs, "shots_on_target": _int(row.get("HST")), "corners": hc,
                    "fouls_committed": _int(row.get("HF")),
                    "yellow_cards": hy, "red_cards": _int(row.get("HR")),
                })
                rows.append({
                    "match_id": m["id"], "team_id": m["away_team_id"], "is_home": False,
                    "shots": as_, "shots_on_target": _int(row.get("AST")), "corners": ac,
                    "fouls_committed": _int(row.get("AF")),
                    "yellow_cards": ay, "red_cards": _int(row.get("AR")),
                })
        for b in _batches(rows, 1000):
            sb.table("scouting_match_team_stats").insert(b).execute()
        grand += len(rows)
        print(f"{league}: {len(rows)} filas de stats ({len(rows)//2} partidos)")

    print(f"Listo. {grand} filas de stats de clubes.")


if __name__ == "__main__":
    run()
