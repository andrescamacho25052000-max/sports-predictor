"""
build_nba_elo.py
================
Construye el modelo NBA a partir de partidos históricos de API-Sports:

1. Elo por equipo (secuencial, con regresión a la media entre temporadas y
   multiplicador por margen de victoria, estilo FiveThirtyEight).
2. Promedios de anotación por equipo (puntos a favor / en contra) de la
   temporada más reciente accesible — para estimar el total de puntos.
3. Calibración de liga (media y desviación del total y del margen) para las
   probabilidades over/under y de hándicap.

Salida (en ml/data/):
- nba_elo.json         → {equipo: elo_rating}
- nba_team_stats.json  → {equipo: {pts_for_avg, pts_against_avg, games, logo}}
- nba_meta.json        → calibración de liga + metadatos

Uso:  python -m ml.build_nba_elo
"""

import json
import math
import statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import basketball_api as bball

DATA_DIR = Path(__file__).parent / "data"

K_FACTOR = 20.0
HOME_ADV = 100.0          # ventaja de localía en puntos Elo (~+3.5 pts)
SEASON_REGRESSION = 0.25  # cuánto se regresa a 1500 entre temporadas


def _expected(elo_a: float, elo_b: float) -> float:
    """Probabilidad esperada de que A gane según Elo (sin localía)."""
    return 1.0 / (1.0 + 10 ** (-(elo_a - elo_b) / 400.0))


def _mov_multiplier(margin: int, elo_diff_winner: float) -> float:
    """Multiplicador por margen de victoria (atenúa el 'autocorrelación' del Elo)."""
    return math.log(abs(margin) + 1.0) * (2.2 / ((elo_diff_winner * 0.001) + 2.2))


def rebuild() -> dict:
    """Descarga el historial, recalcula Elo + stats y escribe los JSON.

    Returns:
        dict: Resumen con conteos y la calibración de liga.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    elo: dict[str, float] = {}
    last_season_games: list[dict] = []
    seasons_used = []

    for season in bball.BUILD_SEASONS:
        games = bball.get_season_games(season)
        if not games:
            continue
        seasons_used.append(season)

        # Filtra equipos no-NBA (All-Star, Rising Stars, etc.): un equipo real
        # juega decenas de partidos por temporada; los del All-Star, 1-2.
        appearances: Counter = Counter()
        for g in games:
            appearances[g["home"]] += 1
            appearances[g["away"]] += 1
        valid = {t for t, c in appearances.items() if c >= 20}
        games = [g for g in games if g["home"] in valid and g["away"] in valid]

        # Regresión a la media al iniciar cada nueva temporada.
        for t in elo:
            elo[t] = (1 - SEASON_REGRESSION) * elo[t] + SEASON_REGRESSION * 1500.0

        for g in games:
            h, a = g["home"], g["away"]
            eh = elo.get(h, 1500.0)
            ea = elo.get(a, 1500.0)
            exp_h = _expected(eh + HOME_ADV, ea)
            home_won = g["home_pts"] > g["away_pts"]
            actual_h = 1.0 if home_won else 0.0
            margin = g["home_pts"] - g["away_pts"]
            winner_diff = (eh - ea) if home_won else (ea - eh)
            mult = _mov_multiplier(margin, winner_diff)
            delta = K_FACTOR * mult * (actual_h - exp_h)
            elo[h] = eh + delta
            elo[a] = ea - delta

        last_season_games = games  # nos quedamos con la última temporada con datos

    if not last_season_games:
        raise RuntimeError("No se pudieron descargar partidos NBA (¿API_SPORTS_KEY?).")

    # ── Stats de anotación (última temporada accesible) ──────────────────────
    acc: dict[str, dict] = {}
    totals, margins = [], []
    for g in last_season_games:
        totals.append(g["home_pts"] + g["away_pts"])
        margins.append(g["home_pts"] - g["away_pts"])
        for side, opp in (("home", "away"), ("away", "home")):
            name = g[side]
            d = acc.setdefault(name, {"pf": 0, "pa": 0, "n": 0, "logo": g[f"{side}_logo"]})
            d["pf"] += g[f"{side}_pts"]
            d["pa"] += g[f"{opp}_pts"]
            d["n"] += 1

    team_stats = {
        name: {
            "pts_for_avg":     round(d["pf"] / d["n"], 2),
            "pts_against_avg": round(d["pa"] / d["n"], 2),
            "games":           d["n"],
            "logo":            d["logo"],
        }
        for name, d in acc.items() if d["n"] > 0
    }

    meta = {
        "league_avg_total": round(statistics.mean(totals), 2),
        "total_std":        round(statistics.pstdev(totals), 2),
        "margin_std":       round(statistics.pstdev(margins), 2),
        "home_margin_mean": round(statistics.mean(margins), 2),
        "seasons_used":     seasons_used,
        "scoring_season":   seasons_used[-1] if seasons_used else None,
        "teams":            len(team_stats),
        "built_at":         datetime.now(timezone.utc).isoformat(),
    }

    elo_rounded = {t: round(v, 1) for t, v in elo.items()}
    (DATA_DIR / "nba_elo.json").write_text(
        json.dumps(elo_rounded, indent=2, ensure_ascii=False), encoding="utf-8")
    (DATA_DIR / "nba_team_stats.json").write_text(
        json.dumps(team_stats, indent=2, ensure_ascii=False), encoding="utf-8")
    (DATA_DIR / "nba_meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    return {"teams_elo": len(elo_rounded), "teams_stats": len(team_stats), **meta}


if __name__ == "__main__":
    summary = rebuild()
    print(json.dumps(summary, indent=2, ensure_ascii=False))
