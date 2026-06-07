"""
ml/build_dataset.py — Feature engineering a partir de los JSON descargados.

Para cada partido calcula las features usando SOLO datos ANTERIORES a ese
partido (sin filtración del futuro). Genera ml/data/dataset.csv.

Uso:
    cd backend
    python -m ml.build_dataset
"""
import sys, os, json
from datetime import datetime
from collections import defaultdict
import bisect
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# ─── Parseo ──────────────────────────────────────────────────────────────────

def _parse(m: dict) -> dict | None:
    sc = m.get("score", {}).get("fullTime", {})
    h, a = sc.get("home"), sc.get("away")
    if h is None or a is None or m.get("status") != "FINISHED":
        return None
    date_str = (m.get("utcDate") or "")[:10]
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return None
    return {
        "date":       date,
        "home_id":    m["homeTeam"]["id"],
        "away_id":    m["awayTeam"]["id"],
        "home_goals": int(h),
        "away_goals": int(a),
    }


# ─── Feature helpers ─────────────────────────────────────────────────────────

def _form(matches: list, team_id: int) -> tuple:
    """(wins, draws, losses, gf, ga) para una lista de partidos."""
    wins = draws = losses = gf = ga = 0
    for m in matches:
        is_home = m["home_id"] == team_id
        f = m["home_goals"] if is_home else m["away_goals"]
        c = m["away_goals"] if is_home else m["home_goals"]
        gf += f; ga += c
        if f > c:   wins += 1
        elif f == c: draws += 1
        else:        losses += 1
    return wins, draws, losses, gf, ga


def _h2h(all_sorted: list, home_id: int, away_id: int, before_date: datetime, n: int = 10):
    """Ratio de victorias del local en los últimos n H2H antes de before_date."""
    ids = {home_id, away_id}
    h2h = [m for m in all_sorted if m["date"] < before_date and {m["home_id"], m["away_id"]} == ids][-n:]
    if not h2h:
        return 0.45, 0.27
    hw = sum(1 for m in h2h if
             (m["home_id"] == home_id and m["home_goals"] > m["away_goals"]) or
             (m["away_id"] == home_id and m["away_goals"] > m["home_goals"]))
    dr = sum(1 for m in h2h if m["home_goals"] == m["away_goals"])
    t  = len(h2h)
    return hw / t, dr / t


# ─── Dataset builder ─────────────────────────────────────────────────────────

def build_dataset() -> pd.DataFrame:
    # 1 — cargar todos los JSON
    all_matches = []
    for fname in os.listdir(DATA_DIR):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(DATA_DIR, fname), encoding="utf-8") as f:
            for m in json.load(f):
                parsed = _parse(m)
                if parsed:
                    all_matches.append(parsed)

    all_matches.sort(key=lambda x: x["date"])
    print(f"  Partidos válidos cargados: {len(all_matches)}")

    # 2 — índice por equipo para búsqueda eficiente
    team_idx: dict[int, list] = defaultdict(list)
    for m in all_matches:
        team_idx[m["home_id"]].append(m)
        team_idx[m["away_id"]].append(m)
    # cada lista ya está ordenada (all_matches está ordenado)

    def last_n(team_id: int, before: datetime, n: int = 5, as_home: bool | None = None):
        lst = team_idx[team_id]
        cut = bisect.bisect_left(lst, before, key=lambda x: x["date"])
        history = lst[:cut]
        if as_home is True:
            history = [m for m in history if m["home_id"] == team_id]
        elif as_home is False:
            history = [m for m in history if m["away_id"] == team_id]
        return history[-n:]

    # 3 — construir filas
    rows = []
    for m in all_matches:
        hid, aid = m["home_id"], m["away_id"]
        bd = m["date"]

        h5 = last_n(hid, bd, 5)
        a5 = last_n(aid, bd, 5)
        if len(h5) < 3 or len(a5) < 3:
            continue   # muy pocos datos previos → no confiable

        hw, hd, hl, hgf, hga = _form(h5, hid)
        aw, ad, al, agf, aga = _form(a5, aid)

        h_home = last_n(hid, bd, 3, as_home=True)
        a_away = last_n(aid, bd, 3, as_home=False)
        h_hw, h_hd, h_hl, _, _ = _form(h_home, hid) if h_home else (1, 1, 1, 0, 0)
        a_aw, a_ad, a_al, _, _ = _form(a_away, aid) if a_away else (1, 1, 1, 0, 0)

        h2h_hr, h2h_dr = _h2h(all_matches, hid, aid, bd)

        if m["home_goals"] > m["away_goals"]:    result = 0   # local
        elif m["home_goals"] == m["away_goals"]: result = 1   # empate
        else:                                     result = 2   # visitante

        rows.append({
            "home_wins_5":     hw,   "home_draws_5":     hd,   "home_losses_5":     hl,
            "home_gf_5":       hgf,  "home_ga_5":        hga,
            "away_wins_5":     aw,   "away_draws_5":     ad,   "away_losses_5":     al,
            "away_gf_5":       agf,  "away_ga_5":        aga,
            "home_home_wins":  h_hw, "home_home_draws":  h_hd, "home_home_losses":  h_hl,
            "away_away_wins":  a_aw, "away_away_draws":  a_ad, "away_away_losses":  a_al,
            "h2h_home_ratio":  h2h_hr,
            "h2h_draw_ratio":  h2h_dr,
            "result":          result,
        })

    df = pd.DataFrame(rows)
    out = os.path.join(DATA_DIR, "dataset.csv")
    df.to_csv(out, index=False)

    dist = df["result"].value_counts().rename({0: "Local", 1: "Empate", 2: "Visitante"})
    print(f"  Filas en el dataset: {len(df)}")
    print(f"  Distribución: {dist.to_dict()}")
    print(f"  Guardado en: {out}")
    return df


if __name__ == "__main__":
    print("=" * 55)
    print("  PASO 2 — Feature engineering")
    print("=" * 55)
    build_dataset()
