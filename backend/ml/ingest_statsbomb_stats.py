"""
ml/ingest_statsbomb_stats.py — Stats detalladas + xG (StatsBomb) -> scouting_match_team_stats.

Descarga eventos de StatsBomb Open Data (GitHub, gratis) de torneos de selecciones
y agrega por equipo: posesion, disparos, disparos al arco, xG, pases, precision de
pases, corners, faltas, tarjetas. Cruza con scouting_matches por (fecha, equipos).

Uso:
    python -m ml.ingest_statsbomb_stats --test   # 1 partido, sin base
    python -m ml.ingest_statsbomb_stats          # carga completa
"""
import json
import sys
import time
import urllib.request

import supabase_client as sbc

BASE = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"

# Torneos de selecciones con xG confiable (competition_id, season_id, nombre)
COMPETITIONS = [
    (43, 106, "FIFA World Cup 2022"),
    (43,   3, "FIFA World Cup 2018"),
    (55, 282, "UEFA Euro 2024"),
    (55,  43, "UEFA Euro 2020"),
    (223, 282, "Copa America 2024"),
    (1267, 107, "African Cup of Nations 2023"),
]

# Mundiales historicos (StatsBomb backfill). El xG puede ser parcial/ausente.
COMPETITIONS_HISTORICAL = [
    (43, 55, "FIFA World Cup 1990"),
    (43, 54, "FIFA World Cup 1986"),
    (43, 51, "FIFA World Cup 1974"),
    (43, 272, "FIFA World Cup 1970"),
    (43, 270, "FIFA World Cup 1962"),
    (43, 269, "FIFA World Cup 1958"),
]


def fetch(url, retries=3):
    for a in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                return json.loads(r.read())
        except Exception:
            if a < retries - 1:
                time.sleep(1)
    return None


def extract(events, home_id, away_id):
    """Agrega stats por equipo desde los eventos del partido."""
    s = {p: dict(shots=0, shots_ot=0, xg=0.0, corners=0, fouls=0, yellow=0, red=0,
                 passes=0, passes_ok=0) for p in ("home", "away")}
    for ev in events:
        t = ev.get("type", {}).get("name", "")
        pfx = "home" if ev.get("team", {}).get("id") == home_id else "away"
        if t == "Pass":
            s[pfx]["passes"] += 1
            p = ev.get("pass", {})
            if "outcome" not in p:                 # sin outcome = pase completo
                s[pfx]["passes_ok"] += 1
            if p.get("type", {}).get("name") == "Corner":
                s[pfx]["corners"] += 1
        elif t == "Foul Committed":
            s[pfx]["fouls"] += 1
            card = ev.get("foul_committed", {}).get("card", {}).get("name", "")
            if "Yellow" in card:
                s[pfx]["yellow"] += 1
            elif "Red" in card:
                s[pfx]["red"] += 1
        elif t == "Bad Behaviour":
            card = ev.get("bad_behaviour", {}).get("card", {}).get("name", "")
            if "Yellow" in card:
                s[pfx]["yellow"] += 1
            elif "Red" in card:
                s[pfx]["red"] += 1
        elif t == "Shot":
            sh = ev.get("shot", {})
            s[pfx]["shots"] += 1
            if sh.get("outcome", {}).get("name") in ("Goal", "Saved", "Saved To Post"):
                s[pfx]["shots_ot"] += 1
            s[pfx]["xg"] += sh.get("statsbomb_xg", 0) or 0
    # posesion = share de pases
    tp = s["home"]["passes"] + s["away"]["passes"]
    for p in ("home", "away"):
        s[p]["possession"] = round(s[p]["passes"] / tp * 100, 1) if tp else None
        s[p]["pass_acc"] = round(s[p]["passes_ok"] / s[p]["passes"] * 100, 1) if s[p]["passes"] else None
        s[p]["xg"] = round(s[p]["xg"], 3)
    return s


def _norm(x):
    return (x or "").strip().lower()


def _build_index(sb, since="2018-01-01", category=None):
    """(fecha, local_norm, visitante_norm) -> info de scouting_matches."""
    idx, off = {}, 0
    while True:
        q = (sb.table("scouting_matches")
               .select("id,match_date,home_team,away_team,home_team_id,away_team_id")
               .gte("match_date", since))
        if category:
            q = q.eq("category", category)
        res = q.range(off, off + 999).execute()
        data = res.data or []
        for m in data:
            idx[(m["match_date"], _norm(m["home_team"]), _norm(m["away_team"]))] = m
        if len(data) < 1000:
            break
        off += 1000
    return idx


def _find(idx, date, home, away):
    m = idx.get((date, _norm(home), _norm(away)))
    if m:
        return m, False
    m = idx.get((date, _norm(away), _norm(home)))   # por si vienen invertidos
    return (m, True) if m else (None, False)


def _row(match_id, team_id, is_home, st):
    return {
        "match_id": match_id, "team_id": team_id, "is_home": is_home,
        "possession": st["possession"], "shots": st["shots"], "shots_on_target": st["shots_ot"],
        "xg": st["xg"], "corners": st["corners"], "fouls_committed": st["fouls"],
        "yellow_cards": st["yellow"], "red_cards": st["red"],
        "passes": st["passes"], "passes_completed": st["passes_ok"], "pass_accuracy": st["pass_acc"],
    }


def run(test=False, historical=False):
    comps = COMPETITIONS_HISTORICAL if historical else COMPETITIONS
    sb = None if test else sbc.get_client()
    if test:
        idx = {}
    elif historical:
        idx = _build_index(sb, since="1950-01-01", category="mundial")
        print(f"Partidos Mundiales indexados: {len(idx)}")
    else:
        idx = _build_index(sb)
        print(f"Partidos scouting indexados (desde 2018): {len(idx)}")

    rows_out, matched, unmatched = [], 0, 0
    for comp_id, season_id, name in comps:
        matches = fetch(f"{BASE}/matches/{comp_id}/{season_id}.json")
        if not matches:
            print(f"{name}: sin datos"); continue
        print(f"{name}: {len(matches)} partidos")
        for m in matches:
            hid, aid = m["home_team"]["home_team_id"], m["away_team"]["away_team_id"]
            hn, an = m["home_team"]["home_team_name"], m["away_team"]["away_team_name"]
            events = fetch(f"{BASE}/events/{m['match_id']}.json")
            if not events:
                continue
            st = extract(events, hid, aid)
            if test:
                print(f"  {m['match_date']} {hn} vs {an}")
                print(f"    LOCAL  pos {st['home']['possession']}% tiros {st['home']['shots']} "
                      f"(al arco {st['home']['shots_ot']}) xG {st['home']['xg']} pases {st['home']['passes']} "
                      f"({st['home']['pass_acc']}%) corners {st['home']['corners']} amarillas {st['home']['yellow']}")
                print(f"    VISIT  pos {st['away']['possession']}% tiros {st['away']['shots']} xG {st['away']['xg']}")
                return
            sm, swap = _find(idx, m["match_date"], hn, an)
            if not sm:
                unmatched += 1
                continue
            matched += 1
            # si vino invertido, ojo con is_home/team_id (usamos los de scouting)
            h_team_id, a_team_id = sm["home_team_id"], sm["away_team_id"]
            if not swap:
                rows_out.append(_row(sm["id"], h_team_id, True, st["home"]))
                rows_out.append(_row(sm["id"], a_team_id, False, st["away"]))
            else:
                rows_out.append(_row(sm["id"], a_team_id, False, st["home"]))
                rows_out.append(_row(sm["id"], h_team_id, True, st["away"]))
            time.sleep(0.05)

    print(f"Partidos cruzados: {matched} | sin cruce: {unmatched} | filas: {len(rows_out)}")
    if rows_out:
        for i in range(0, len(rows_out), 500):
            sb.table("scouting_match_team_stats").insert(rows_out[i:i + 500]).execute()
        print(f"Listo. {len(rows_out)} filas en scouting_match_team_stats.")


if __name__ == "__main__":
    run(test="--test" in sys.argv, historical="--historical" in sys.argv)
