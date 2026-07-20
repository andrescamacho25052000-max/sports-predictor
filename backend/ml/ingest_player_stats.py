"""
ml/ingest_player_stats.py — Estadisticas por jugador y partido (StatsBomb)
-> scouting_player_match_stats (y crea/vincula jugadores en scouting_players).

Agrega, desde los eventos de StatsBomb de torneos de selecciones, las stats de
cada jugador en cada partido: goles, asistencias, tiros, xG, pases, pases clave,
faltas, tarjetas y posicion. Vincula cada jugador a scouting_players (por nombre;
si no existe, lo crea). Enriquece la 'tarjeta de jugador' con datos por partido.

Uso:
    python -m ml.ingest_player_stats --test   # 1 partido, sin base
    python -m ml.ingest_player_stats           # carga completa
"""
import json
import sys
import time
import urllib.request
from collections import defaultdict, Counter

import supabase_client as sbc
from ml.ingest_statsbomb_stats import COMPETITIONS, BASE, _build_index, _norm


def fetch(url, retries=3):
    for a in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=25) as r:
                return json.loads(r.read())
        except Exception:
            if a < retries - 1:
                time.sleep(1)
    return None


def aggregate_players(events, home_sb_id):
    """Agrega stats por jugador desde los eventos. Devuelve {sb_pid: {...}}."""
    P = defaultdict(lambda: {
        "name": None, "sb_team": None, "is_home": None, "positions": Counter(),
        "goals": 0, "assists": 0, "shots": 0, "shots_ot": 0, "xg": 0.0,
        "passes": 0, "passes_ok": 0, "key_passes": 0, "fouls": 0, "yellow": 0, "red": 0,
    })
    for ev in events:
        pl = ev.get("player") or {}
        pid = pl.get("id")
        if pid is None:
            continue
        d = P[pid]
        d["name"] = pl.get("name")
        team = ev.get("team") or {}
        d["sb_team"] = team.get("name")
        d["is_home"] = (team.get("id") == home_sb_id)
        pos = (ev.get("position") or {}).get("name")
        if pos:
            d["positions"][pos] += 1
        t = ev.get("type", {}).get("name", "")
        if t == "Pass":
            d["passes"] += 1
            p = ev.get("pass", {})
            if "outcome" not in p:
                d["passes_ok"] += 1
            if p.get("shot_assist") or p.get("goal_assist"):
                d["key_passes"] += 1
            if p.get("goal_assist"):
                d["assists"] += 1
        elif t == "Shot":
            sh = ev.get("shot", {})
            d["shots"] += 1
            if sh.get("outcome", {}).get("name") in ("Goal", "Saved", "Saved To Post"):
                d["shots_ot"] += 1
            if sh.get("outcome", {}).get("name") == "Goal":
                d["goals"] += 1
            d["xg"] += sh.get("statsbomb_xg", 0) or 0
        elif t == "Foul Committed":
            d["fouls"] += 1
            card = ev.get("foul_committed", {}).get("card", {}).get("name", "")
            if "Yellow" in card:
                d["yellow"] += 1
            elif "Red" in card:
                d["red"] += 1
        elif t == "Bad Behaviour":
            card = ev.get("bad_behaviour", {}).get("card", {}).get("name", "")
            if "Yellow" in card:
                d["yellow"] += 1
            elif "Red" in card:
                d["red"] += 1
    return P


def run(test=False):
    if test:
        m = fetch(f"{BASE}/matches/43/106.json")[0]
        ev = fetch(f"{BASE}/events/{m['match_id']}.json")
        P = aggregate_players(ev, m["home_team"]["home_team_id"])
        print(f"{m['match_date']} {m['home_team']['home_team_name']} vs {m['away_team']['away_team_name']}")
        top = sorted(P.values(), key=lambda x: (x["goals"], x["xg"]), reverse=True)[:5]
        for d in top:
            pos = d["positions"].most_common(1)[0][0] if d["positions"] else "?"
            print(f"  {d['name']} ({pos}): {d['goals']}g {d['assists']}a | tiros {d['shots']} "
                  f"xG {round(d['xg'],2)} | pases {d['passes']} clave {d['key_passes']} | amar {d['yellow']}")
        return

    sb = sbc.get_client()
    idx = _build_index(sb)
    print(f"Partidos scouting indexados: {len(idx)}")

    # Mapa de jugadores existentes: nombre normalizado -> id, e indice por token.
    name_to_id, token_idx = {}, defaultdict(list)
    off = 0
    while True:
        res = sb.table("scouting_players").select("id,name").range(off, off + 999).execute()
        data = res.data or []
        for r in data:
            n = _norm(r["name"])
            name_to_id[n] = r["id"]
            toks = n.split()
            for tk in toks:                      # indexar por TODOS los tokens
                token_idx[tk].append((frozenset(toks), r["id"]))
        if len(data) < 1000:
            break
        off += 1000
    print(f"Jugadores existentes: {len(name_to_id)}")

    def resolve(sb_name):
        """Empareja el nombre de StatsBomb con un jugador existente (o None)."""
        n = _norm(sb_name)
        if n in name_to_id:
            return name_to_id[n]
        sb_toks = set(n.split())
        # Candidato: existente cuyo nombre (>=2 tokens) esta contenido en el de StatsBomb.
        best_id, best_len, seen = None, 0, set()
        for tk in sb_toks:
            for exist_toks, pid in token_idx.get(tk, []):
                if pid in seen:
                    continue
                seen.add(pid)
                if len(exist_toks) >= 2 and exist_toks <= sb_toks and len(exist_toks) > best_len:
                    best_id, best_len = pid, len(exist_toks)
        return best_id

    # Recolectar aggregates por partido (fetch de eventos una vez)
    per_match = []   # (scouting_match, home_team_id, away_team_id, {pid: agg})
    new_players = {}  # sb_name -> {position, sb_id}
    for comp_id, season_id, name in COMPETITIONS:
        matches = fetch(f"{BASE}/matches/{comp_id}/{season_id}.json") or []
        print(f"{name}: {len(matches)} partidos")
        for m in matches:
            hn, an = m["home_team"]["home_team_name"], m["away_team"]["away_team_name"]
            sm = idx.get((m["match_date"], _norm(hn), _norm(an)))
            if not sm:
                continue
            ev = fetch(f"{BASE}/events/{m['match_id']}.json")
            if not ev:
                continue
            P = aggregate_players(ev, m["home_team"]["home_team_id"])
            per_match.append((sm, P))
            for pid, d in P.items():
                if resolve(d["name"]) is None and d["name"] not in new_players:
                    pos = d["positions"].most_common(1)[0][0] if d["positions"] else None
                    new_players[d["name"]] = pos
            time.sleep(0.03)

    # Crear jugadores nuevos y refrescar el mapa
    if new_players:
        rows = [{"name": nm, "position": pos} for nm, pos in new_players.items()]
        for i in range(0, len(rows), 500):
            sb.table("scouting_players").upsert(rows[i:i + 500], on_conflict="name").execute()
        # refrescar solo los nuevos
        for i in range(0, len(rows), 200):
            names = [r["name"] for r in rows[i:i + 200]]
            got = sb.table("scouting_players").select("id,name").in_("name", names).execute().data or []
            for r in got:
                name_to_id[_norm(r["name"])] = r["id"]
    print(f"Jugadores nuevos creados: {len(new_players)}")

    # Construir e insertar player_match_stats
    stat_rows = []
    for sm, P in per_match:
        for pid, d in P.items():
            player_id = name_to_id.get(_norm(d["name"])) or resolve(d["name"])
            if not player_id:
                continue
            team_id = sm["home_team_id"] if d["is_home"] else sm["away_team_id"]
            pos = d["positions"].most_common(1)[0][0] if d["positions"] else None
            stat_rows.append({
                "match_id": sm["id"], "team_id": team_id, "player_id": player_id,
                "goals": d["goals"], "assists": d["assists"], "shots": d["shots"],
                "shots_on_target": d["shots_ot"], "xg": round(d["xg"], 3),
                "passes": d["passes"], "passes_completed": d["passes_ok"],
                "key_passes": d["key_passes"], "fouls": d["fouls"],
                "raw": {"position": pos, "yellow": d["yellow"], "red": d["red"]},
            })
    for i in range(0, len(stat_rows), 1000):
        sb.table("scouting_player_match_stats").insert(stat_rows[i:i + 1000]).execute()
        print(f"  ... {min(i+1000,len(stat_rows))}/{len(stat_rows)}")
    print(f"Listo. {len(stat_rows)} filas en scouting_player_match_stats.")


if __name__ == "__main__":
    run(test="--test" in sys.argv)
