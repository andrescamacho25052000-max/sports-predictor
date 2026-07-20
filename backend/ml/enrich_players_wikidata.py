"""
ml/enrich_players_wikidata.py — Perfil de jugadores (edad, club actual, historial)
desde Wikidata (SPARQL, gratis).

Rellena en scouting_players: birthdate, position, current_club, team_history (jsonb)
y wikidata_id. Por escala, enriquece un subconjunto PRIORITARIO: los jugadores con
estadisticas de partido (torneos recientes). Es RESUMIBLE (solo procesa los que aun
no tienen birthdate).

Uso:  python -m ml.enrich_players_wikidata [--limit N]
"""
import sys
import time

import requests

import supabase_client as sbc

SPARQL = "https://query.wikidata.org/sparql"
UA = {"User-Agent": "SportsPredictor/1.0 (data research; contact via app)"}

_NATIONAL_KW = ["selecci", "national", "nacional", "sub-", "sub ", " u-", "u20", "u21",
                "u23", "u17", "u19", "olymp", "olimp", "olímp"]


def _is_national(label: str) -> bool:
    l = (label or "").lower()
    return any(k in l for k in _NATIONAL_KW)


def query_player(name: str):
    """Consulta Wikidata por nombre. Devuelve dict de perfil o None (o 'ambiguo')."""
    n = name.replace("\\", "").replace('"', "")
    q = f'''SELECT ?player ?dob ?posLabel ?teamLabel ?start ?end WHERE {{
      VALUES ?lbl {{ "{n}"@es "{n}"@en }}
      ?player rdfs:label ?lbl ; wdt:P106 wd:Q937857 .
      OPTIONAL {{ ?player wdt:P569 ?dob }}
      OPTIONAL {{ ?player wdt:P413 ?pos }}
      OPTIONAL {{ ?player p:P54 ?st . ?st ps:P54 ?team .
                 OPTIONAL {{ ?st pq:P580 ?start }} OPTIONAL {{ ?st pq:P582 ?end }} }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "es,en". }}
    }} LIMIT 200'''
    try:
        r = requests.get(SPARQL, params={"query": q, "format": "json"}, headers=UA, timeout=40)
        if r.status_code != 200:
            return None
        rows = r.json()["results"]["bindings"]
    except Exception:
        return None
    if not rows:
        return None

    entities = {row["player"]["value"] for row in rows}
    if len(entities) != 1:
        return "ambiguo"   # varias personas con ese nombre: no arriesgamos

    qid = rows[0]["player"]["value"].rsplit("/", 1)[-1]
    dob = next((row["dob"]["value"][:10] for row in rows if "dob" in row), None)
    pos = next((row["posLabel"]["value"] for row in rows if "posLabel" in row
                and not row["posLabel"]["value"].startswith("http")), None)

    teams = {}
    for row in rows:
        t = row.get("teamLabel", {}).get("value")
        if not t or t.startswith("http"):
            continue
        s = row.get("start", {}).get("value", "")[:4] or None
        e = row.get("end", {}).get("value", "")[:4] or None
        key = (t, s)
        if key not in teams:
            teams[key] = {"team": t, "start": s, "end": e, "national": _is_national(t)}

    history = sorted(teams.values(), key=lambda x: (x["start"] or "0000"))
    clubs = [h for h in history if not h["national"]]
    # club actual: club sin fecha de fin (o el de inicio mas reciente)
    active = [c for c in clubs if not c["end"]]
    current = (max(active, key=lambda c: c["start"] or "0000") if active
               else (max(clubs, key=lambda c: c["start"] or "0000") if clubs else None))
    return {
        "wikidata_id": qid, "birthdate": dob, "position": pos,
        "current_club": current["team"] if current else None,
        "team_history": history,
    }


def run(limit=1500):
    sb = sbc.get_client()
    if not sb:
        print("ERROR: sin cliente Supabase."); return

    # Subconjunto prioritario: jugadores con stats de partido, sin perfil aun.
    ids, off = set(), 0
    while True:
        d = sb.table("scouting_player_match_stats").select("player_id").range(off, off + 999).execute().data or []
        for r in d:
            ids.add(r["player_id"])
        if len(d) < 1000:
            break
        off += 1000

    targets = []
    id_list = list(ids)
    for i in range(0, len(id_list), 150):
        got = (sb.table("scouting_players").select("id,name,birthdate")
                 .in_("id", id_list[i:i + 150]).execute().data or [])
        for r in got:
            if not r.get("birthdate"):
                targets.append(r)
    targets = targets[:limit]
    print(f"Jugadores a enriquecer: {len(targets)}")

    ok = amb = miss = 0
    for i, p in enumerate(targets, 1):
        res = query_player(p["name"])
        if res == "ambiguo":
            amb += 1
        elif res:
            sb.table("scouting_players").update({
                "wikidata_id": res["wikidata_id"], "birthdate": res["birthdate"],
                "position": res["position"], "current_club": res["current_club"],
                "team_history": res["team_history"],
            }).eq("id", p["id"]).execute()
            ok += 1
        else:
            miss += 1
        if i % 25 == 0:
            print(f"  ... {i}/{len(targets)} (ok {ok}, ambiguo {amb}, sin dato {miss})")
        time.sleep(0.4)

    print(f"Listo. Enriquecidos {ok} | ambiguos {amb} | sin dato {miss}.")


if __name__ == "__main__":
    lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 1500
    run(limit=lim)
