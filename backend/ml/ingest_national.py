"""
ml/ingest_national.py — Ingesta de partidos de selecciones a scouting_matches.

Fuente: ml/data/international_results.csv (dataset martj42, 1872-2026).
Categoriza cada partido (mundial / eliminatoria / continental / amistoso / otro)
y lo carga a las tablas scouting_teams y scouting_matches en Supabase.

Uso:
    python -m ml.ingest_national --dry-run     # valida sin tocar la base
    python -m ml.ingest_national               # inserta de verdad
"""
import csv
import os
import sys

import supabase_client as sbc

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CSV_PATH = os.path.join(DATA_DIR, "international_results.csv")

# Continentales (campeonatos + sus eliminatorias)
_CONTINENTAL = [
    "copa am", "uefa euro", "european championship", "african cup of nations",
    "afc asian cup", "gold cup", "concacaf", "ofc nations", "nations league",
    "confederations cup", "conmebol",
]


def categorize(tournament: str) -> str:
    t = (tournament or "").strip()
    tl = t.lower()
    if t == "FIFA World Cup":
        return "mundial"
    if "world cup qualification" in tl:
        return "eliminatoria"
    if any(c in tl for c in _CONTINENTAL):
        return "continental"
    if t == "Friendly":
        return "amistoso"
    return "otro"


def _winner(hg, ag) -> str | None:
    if hg is None or ag is None:
        return None
    return "Local" if hg > ag else "Visitante" if ag > hg else "Empate"


def _int(v):
    v = (v or "").strip()
    try:
        return int(v)
    except ValueError:
        return None


def load_rows() -> tuple[list[dict], set]:
    """Lee el CSV y devuelve (filas de partidos, conjunto de equipos)."""
    matches, teams = [], set()
    with open(CSV_PATH, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            home, away = r["home_team"].strip(), r["away_team"].strip()
            teams.add(home); teams.add(away)
            hg, ag = _int(r["home_score"]), _int(r["away_score"])
            matches.append({
                "source": "martj42/international_results",
                "competition_type": "national",
                "category":   categorize(r["tournament"]),
                "tournament": r["tournament"].strip(),
                "match_date": r["date"].strip(),
                "home_team":  home,
                "away_team":  away,
                "home_goals": hg,
                "away_goals": ag,
                "winner":     _winner(hg, ag),
                "neutral":    (r.get("neutral", "").strip().upper() == "TRUE"),
                "city":       (r.get("city") or "").strip() or None,
                "country":    (r.get("country") or "").strip() or None,
            })
    return matches, teams


def _batches(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def run(dry_run: bool = False):
    matches, teams = load_rows()

    from collections import Counter
    cats = Counter(m["category"] for m in matches)
    print(f"Partidos: {len(matches)} | equipos: {len(teams)}")
    print("Por categoria:")
    for c in ("mundial", "eliminatoria", "continental", "amistoso", "otro"):
        print(f"  {c:12s}: {cats.get(c, 0)}")

    if dry_run:
        print("\n[DRY-RUN] No se inserto nada. Ejemplos:")
        for c in ("mundial", "eliminatoria", "continental"):
            ex = next((m for m in matches if m["category"] == c), None)
            if ex:
                print(f"  [{c}] {ex['match_date']} {ex['home_team']} {ex['home_goals']}-{ex['away_goals']} {ex['away_team']} ({ex['tournament']})")
        return

    sb = sbc.get_client()
    if not sb:
        print("ERROR: sin cliente Supabase (revisa .env).")
        return

    # 1) Equipos (upsert por nombre)
    team_rows = [{"name": t, "type": "national"} for t in sorted(teams)]
    for b in _batches(team_rows, 500):
        sb.table("scouting_teams").upsert(b, on_conflict="name").execute()
    print(f"Equipos cargados: {len(team_rows)}")

    # 2) Mapa nombre -> id
    name_to_id, offset = {}, 0
    while True:
        res = sb.table("scouting_teams").select("id,name").range(offset, offset + 999).execute()
        data = res.data or []
        for row in data:
            name_to_id[row["name"]] = row["id"]
        if len(data) < 1000:
            break
        offset += 1000

    # 3) Partidos (con team_id resueltos), en orden de prioridad
    order = {"mundial": 0, "eliminatoria": 1, "continental": 2, "amistoso": 3, "otro": 4}
    matches.sort(key=lambda m: (order.get(m["category"], 9), m["match_date"]))

    # Deduplicar por la clave unica (algunos partidos vienen repetidos en la fuente).
    # El upsert falla si el mismo lote trae dos filas con la misma clave.
    seen, unique = set(), []
    for m in matches:
        key = (m["tournament"], m["match_date"], m["home_team"], m["away_team"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(m)
    dropped = len(matches) - len(unique)
    if dropped:
        print(f"Duplicados descartados: {dropped}")
    matches = unique

    for m in matches:
        m["home_team_id"] = name_to_id.get(m["home_team"])
        m["away_team_id"] = name_to_id.get(m["away_team"])

    total = 0
    for b in _batches(matches, 1000):
        sb.table("scouting_matches").upsert(
            b, on_conflict="tournament,match_date,home_team,away_team"
        ).execute()
        total += len(b)
        print(f"  ... {total}/{len(matches)} partidos")
    print(f"Listo. {total} partidos cargados en scouting_matches.")


if __name__ == "__main__":
    run(dry_run="--dry-run" in sys.argv)
