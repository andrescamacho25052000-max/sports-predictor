"""
ml/ingest_goalscorers.py — Goleadores -> scouting_match_events.

Fuente: repo martj42 (goalscorers.csv). Cada gol trae goleador, minuto, si fue
penal o autogol. Se cruza con scouting_matches por (fecha, local, visitante) y se
guarda en scouting_match_events. El nombre del goleador va en `detail` (jsonb).

Uso:  python -m ml.ingest_goalscorers
"""
import csv
import io

import requests

import supabase_client as sbc

URL = "https://raw.githubusercontent.com/martj42/international_results/master/goalscorers.csv"
UA = {"User-Agent": "Mozilla/5.0"}


def _minute(v):
    """Parsea el minuto; separa el tiempo agregado (p.ej. '45+2')."""
    v = (v or "").strip()
    if not v:
        return None, None
    if "+" in v:
        base, _, extra = v.partition("+")
        try:
            return int(base), int(extra)
        except ValueError:
            return None, None
    try:
        return int(v), None
    except ValueError:
        return None, None


def _fetch_match_index(sb) -> dict:
    """Trae todos los partidos y arma el indice (fecha, local, visitante) -> info."""
    index, offset = {}, 0
    while True:
        res = (sb.table("scouting_matches")
                 .select("id,match_date,home_team,away_team,home_team_id,away_team_id")
                 .range(offset, offset + 999).execute())
        data = res.data or []
        for m in data:
            index[(m["match_date"], m["home_team"], m["away_team"])] = m
        if len(data) < 1000:
            break
        offset += 1000
    return index


def _batches(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def run():
    sb = sbc.get_client()
    if not sb:
        print("ERROR: sin cliente Supabase.")
        return

    existing = sb.table("scouting_match_events").select("id", count="exact").limit(1).execute().count
    if existing:
        print(f"Ya hay {existing} eventos cargados. Aborto para no duplicar.")
        return

    r = requests.get(URL, timeout=60, headers=UA)
    r.encoding = "utf-8"
    goals = list(csv.DictReader(io.StringIO(r.text)))
    print(f"Goles en la fuente: {len(goals)}")

    print("Indexando partidos...")
    index = _fetch_match_index(sb)
    print(f"Partidos indexados: {len(index)}")

    events, sin_match = [], 0
    for g in goals:
        key = (g["date"].strip(), g["home_team"].strip(), g["away_team"].strip())
        m = index.get(key)
        if not m:
            sin_match += 1
            continue
        scoring = g["team"].strip()
        team_id = m["home_team_id"] if scoring == m["home_team"] else m["away_team_id"]
        own = g.get("own_goal", "").strip().upper() == "TRUE"
        pen = g.get("penalty", "").strip().upper() == "TRUE"
        etype = "own_goal" if own else "penalty_goal" if pen else "goal"
        minute, extra = _minute(g.get("minute"))
        events.append({
            "match_id":   m["id"],
            "team_id":    team_id,
            "minute":     minute,
            "extra_minute": extra,
            "event_type": etype,
            "detail":     {"scorer": g["scorer"].strip(), "penalty": pen, "own_goal": own,
                           "scoring_team": scoring},
        })

    print(f"Eventos a insertar: {len(events)} | goles sin partido: {sin_match}")
    total = 0
    for b in _batches(events, 1000):
        sb.table("scouting_match_events").insert(b).execute()
        total += len(b)
        print(f"  ... {total}/{len(events)}")
    print(f"Listo. {total} goles cargados en scouting_match_events.")


if __name__ == "__main__":
    run()
