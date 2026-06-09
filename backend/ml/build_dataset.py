"""
ml/build_dataset.py — Feature engineering a partir de los JSON descargados.

Para cada partido calcula las features usando SOLO datos ANTERIORES a ese
partido (sin filtración del futuro). Genera ml/data/dataset.csv.

Features nuevas v2:
  - elo_diff            : diferencia de Elo (local − visitante) antes del partido
  - elo_home_expected   : probabilidad esperada del local según Elo
  - home_pts_per_game   : puntos por partido del local en esa liga/temporada
  - away_pts_per_game   : puntos por partido del visitante en esa liga/temporada

Uso:
    cd backend
    python -m ml.build_dataset
"""
import sys, os, json
from datetime import datetime
from collections import defaultdict
import bisect
import pandas as pd

from ml.elo import EloSystem

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# ─── Parseo ──────────────────────────────────────────────────────────────────

def _parse(m: dict, league: str = "", season: int = 0) -> dict | None:
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
        "league":     league,
        "season":     season,
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


def _ppg(points_list: list) -> float:
    """Puntos por partido acumulados. Neutral = 1.0 si no hay datos."""
    if not points_list:
        return 1.0
    return sum(points_list) / len(points_list)


# ─── Dataset builder ─────────────────────────────────────────────────────────

def build_dataset() -> pd.DataFrame:
    # 1 — cargar todos los JSON con info de liga/temporada
    all_matches = []
    for fname in sorted(os.listdir(DATA_DIR)):
        if not fname.endswith(".json") or fname == "elo_ratings.json":
            continue
        # Formato esperado: CODE_SEASON.json (ej. PL_2023.json)
        parts = fname[:-5].split("_")
        league_code = parts[0] if len(parts) >= 2 else ""
        try:
            season_year = int(parts[-1])
        except ValueError:
            season_year = 0

        with open(os.path.join(DATA_DIR, fname), encoding="utf-8") as f:
            for m in json.load(f):
                parsed = _parse(m, league_code, season_year)
                if parsed:
                    all_matches.append(parsed)

    all_matches.sort(key=lambda x: x["date"])
    print(f"  Partidos válidos cargados: {len(all_matches)}")

    # 2 — índice por equipo para búsqueda eficiente de forma
    team_idx: dict[int, list] = defaultdict(list)
    for m in all_matches:
        team_idx[m["home_id"]].append(m)
        team_idx[m["away_id"]].append(m)

    def last_n(team_id: int, before: datetime, n: int = 5, as_home: bool | None = None):
        lst = team_idx[team_id]
        cut = bisect.bisect_left(lst, before, key=lambda x: x["date"])
        history = lst[:cut]
        if as_home is True:
            history = [m for m in history if m["home_id"] == team_id]
        elif as_home is False:
            history = [m for m in history if m["away_id"] == team_id]
        return history[-n:]

    # 3 — estado acumulativo: Elo y puntos por liga/temporada
    elo = EloSystem()
    # key = (team_id, league_code, season_year) → lista de puntos obtenidos
    season_pts: dict[tuple, list] = defaultdict(list)

    # 4 — construir filas
    rows = []
    for m in all_matches:
        hid, aid = m["home_id"], m["away_id"]
        bd = m["date"]
        lg, seas = m["league"], m["season"]

        h5 = last_n(hid, bd, 5)
        a5 = last_n(aid, bd, 5)
        if len(h5) < 3 or len(a5) < 3:
            # Actualizar Elo de todos modos para que los ratings sean correctos
            elo.update(hid, aid, m["home_goals"], m["away_goals"])
            _update_season_pts(season_pts, hid, aid, lg, seas, m["home_goals"], m["away_goals"])
            continue

        hw, hd, hl, hgf, hga = _form(h5, hid)
        aw, ad, al, agf, aga = _form(a5, aid)

        h_home = last_n(hid, bd, 3, as_home=True)
        a_away = last_n(aid, bd, 3, as_home=False)
        h_hw, h_hd, h_hl, _, _ = _form(h_home, hid) if h_home else (1, 1, 1, 0, 0)
        a_aw, a_ad, a_al, _, _ = _form(a_away, aid) if a_away else (1, 1, 1, 0, 0)

        h2h_hr, h2h_dr = _h2h(all_matches, hid, aid, bd)

        # ── Elo PRE-partido (antes de actualizar) ─────────────────
        elo_diff         = elo.diff(hid, aid)
        elo_home_exp     = elo.expected_home_win(hid, aid)

        # ── Puntos por partido PRE-partido en esa liga/temporada ──
        home_ppg = _ppg(season_pts[(hid, lg, seas)])
        away_ppg = _ppg(season_pts[(aid, lg, seas)])

        if m["home_goals"] > m["away_goals"]:    result = 0
        elif m["home_goals"] == m["away_goals"]: result = 1
        else:                                     result = 2

        rows.append({
            "home_wins_5":       hw,   "home_draws_5":       hd,   "home_losses_5":       hl,
            "home_gf_5":         hgf,  "home_ga_5":          hga,
            "away_wins_5":       aw,   "away_draws_5":       ad,   "away_losses_5":       al,
            "away_gf_5":         agf,  "away_ga_5":          aga,
            "home_home_wins":    h_hw, "home_home_draws":    h_hd, "home_home_losses":    h_hl,
            "away_away_wins":    a_aw, "away_away_draws":    a_ad, "away_away_losses":    a_al,
            "h2h_home_ratio":    h2h_hr,
            "h2h_draw_ratio":    h2h_dr,
            "elo_diff":          round(elo_diff, 2),
            "elo_home_expected": round(elo_home_exp, 4),
            "home_pts_per_game": round(home_ppg, 4),
            "away_pts_per_game": round(away_ppg, 4),
            "result":            result,
        })

        # ── Actualizar estado POST-partido ────────────────────────
        elo.update(hid, aid, m["home_goals"], m["away_goals"])
        _update_season_pts(season_pts, hid, aid, lg, seas, m["home_goals"], m["away_goals"])

    # Guardar Elo final (se usa en producción para predicciones en tiempo real)
    elo.save()

    df = pd.DataFrame(rows)
    out = os.path.join(DATA_DIR, "dataset.csv")
    df.to_csv(out, index=False)

    dist = df["result"].value_counts().rename({0: "Local", 1: "Empate", 2: "Visitante"})
    print(f"  Filas en el dataset: {len(df)}")
    print(f"  Distribución: {dist.to_dict()}")
    print(f"  Equipos con Elo calculado: {len(elo.ratings)}")
    print(f"  Top 5 Elo:")
    for tid, rating in elo.top(5):
        print(f"    {tid}: {rating:.0f}")
    print(f"  Guardado en: {out}")
    return df


def _update_season_pts(season_pts, hid, aid, lg, seas, hg, ag):
    """Registra los puntos obtenidos en la liga/temporada tras un partido."""
    if hg > ag:
        season_pts[(hid, lg, seas)].append(3)
        season_pts[(aid, lg, seas)].append(0)
    elif hg == ag:
        season_pts[(hid, lg, seas)].append(1)
        season_pts[(aid, lg, seas)].append(1)
    else:
        season_pts[(hid, lg, seas)].append(0)
        season_pts[(aid, lg, seas)].append(3)


if __name__ == "__main__":
    print("=" * 55)
    print("  PASO 2 — Feature engineering")
    print("=" * 55)
    build_dataset()
