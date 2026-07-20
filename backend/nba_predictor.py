"""
nba_predictor.py
================
Predicción de partidos NBA a partir del modelo construido por
``ml/build_nba_elo.py``. No hace llamadas de red: usa los datos ya calculados.

- Resultado (moneyline): probabilidad de victoria local/visitante vía Elo
  (sin empate — en NBA siempre hay ganador).
- Total de puntos (over/under): se estima el total esperado con los promedios
  de anotación y se usa una aproximación normal calibrada con la liga.
- Hándicap (spread): margen esperado y probabilidad de cubrir, normal calibrada.
"""

import json
import math
from pathlib import Path

DATA_DIR = Path(__file__).parent / "ml" / "data"

HOME_ADV = 100.0  # mismos puntos Elo de localía que en el build

# Líneas de hándicap (puntos) a evaluar, desde la óptica del local.
SPREAD_LINES = [-10.5, -7.5, -5.5, -3.5, -1.5, 1.5, 3.5, 5.5, 7.5, 10.5]

_elo: dict | None = None
_stats: dict | None = None
_meta: dict | None = None


def _load() -> tuple[dict, dict, dict]:
    """Carga (con caché en memoria) los JSON del modelo NBA."""
    global _elo, _stats, _meta
    if _elo is None:
        _elo = _read("nba_elo.json", {})
        _stats = _read("nba_team_stats.json", {})
        _meta = _read("nba_meta.json", {
            "league_avg_total": 225.0, "total_std": 21.0,
            "margin_std": 16.0, "home_margin_mean": 2.0,
        })
    return _elo, _stats, _meta  # type: ignore


def _read(name: str, default):
    p = DATA_DIR / name
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return default


def reload_model() -> None:
    """Invalida la caché para releer los JSON tras un rebuild."""
    global _elo, _stats, _meta
    _elo = _stats = _meta = None


def is_ready() -> bool:
    """True si el modelo tiene datos de Elo construidos."""
    elo, _, _ = _load()
    return bool(elo)


def list_teams() -> list[dict]:
    """Lista de equipos disponibles (nombre + logo) para autocompletado."""
    _, stats, _ = _load()
    return [{"name": n, "logo": s.get("logo", "")} for n, s in sorted(stats.items())]


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def _match_team(name: str, table: dict) -> str | None:
    """Resuelve el nombre de un equipo contra las claves de una tabla."""
    n = _norm(name)
    if not n:
        return None
    for key in table:
        if _norm(key) == n:
            return key
    for key in table:  # coincidencia parcial (p.ej. "Lakers" → "Los Angeles Lakers")
        k = _norm(key)
        if n in k or k in n:
            return key
    return None


def _phi(x: float) -> float:
    """Función de distribución acumulada normal estándar."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _win_prob(elo_home: float, elo_away: float) -> float:
    """Probabilidad de que gane el local (Elo + localía)."""
    return 1.0 / (1.0 + 10 ** (-((elo_home + HOME_ADV) - elo_away) / 400.0))


def annotate_odds(prediction: dict, raw_odds: dict | None) -> dict | None:
    """Cruza las cuotas reales con la predicción NBA y calcula el EV.

    Para los totales se recalcula la probabilidad del modelo en la **línea exacta**
    de la casa de apuestas (no en las líneas predefinidas).

    Args:
        prediction (dict): Salida de ``predict``.
        raw_odds (dict | None): Salida de ``odds_api.get_nba_odds``.

    Returns:
        dict | None: ``{"markets", "best_value", ...}`` o None si no hay cuotas.
    """
    if not raw_odds:
        return None
    _, _, meta = _load()
    std = meta["total_std"]
    exp_total = prediction["expected_points"]["total"]
    markets: dict = {}

    def add(key: str, prob_pct: float | None, odds):
        if prob_pct is None or not odds:
            return
        ev = round((prob_pct / 100.0) * float(odds) - 1.0, 4)
        markets[key] = {"odds": round(float(odds), 2), "prob": round(prob_pct, 1),
                        "ev": ev, "value": ev > 0}

    h2h = raw_odds.get("h2h") or {}
    add("1", prediction["probabilities"]["home_win"], h2h.get("home"))
    add("2", prediction["probabilities"]["away_win"], h2h.get("away"))

    for line_str, sides in (raw_odds.get("totals") or {}).items():
        try:
            line = float(line_str)
        except ValueError:
            continue
        p_over = (1.0 - _phi((line - exp_total) / std)) * 100.0
        add(f"over_{line_str}",  p_over, sides.get("over"))
        add(f"under_{line_str}", 100.0 - p_over, sides.get("under"))

    best_value = sorted(
        ({"market": k, **v} for k, v in markets.items() if v["value"]),
        key=lambda m: m["ev"], reverse=True,
    )
    return {
        "source":          "the-odds-api",
        "bookmaker_count": raw_odds.get("bookmaker_count", 0),
        "commence_time":   raw_odds.get("commence_time"),
        "markets":         markets,
        "best_value":      best_value,
    }


def predict(home: str, away: str) -> dict:
    """Genera la predicción completa de un partido NBA.

    Args:
        home (str): Equipo local.
        away (str): Equipo visitante.

    Returns:
        dict: Probabilidades 1-2, puntos esperados, over/under y hándicap.
    """
    elo, stats, meta = _load()

    hk = _match_team(home, elo) or home
    ak = _match_team(away, elo) or away
    elo_h = elo.get(hk, 1500.0)
    elo_a = elo.get(ak, 1500.0)

    p_home = _win_prob(elo_h, elo_a)
    p_away = 1.0 - p_home

    # ── Puntos esperados ─────────────────────────────────────────────────────
    league_half = meta["league_avg_total"] / 2.0
    sh = stats.get(_match_team(home, stats) or "", {})
    sa = stats.get(_match_team(away, stats) or "", {})
    h_for = sh.get("pts_for_avg", league_half)
    h_against = sh.get("pts_against_avg", league_half)
    a_for = sa.get("pts_for_avg", league_half)
    a_against = sa.get("pts_against_avg", league_half)

    exp_home = (h_for + a_against) / 2.0
    exp_away = (a_for + h_against) / 2.0
    exp_total = exp_home + exp_away

    total_std = meta["total_std"]
    margin_std = meta["margin_std"]

    # ── Over/Under (normal alrededor del total esperado) ─────────────────────
    base = round(exp_total)
    lines = sorted({base - 8.5, base - 4.5, base - 0.5, base + 3.5, base + 7.5})
    over_under = {}
    for line in lines:
        p_over = 1.0 - _phi((line - exp_total) / total_std)
        over_under[f"{line}"] = {
            "over":  round(p_over * 100, 1),
            "under": round((1.0 - p_over) * 100, 1),
        }

    # ── Hándicap (margen local; positivo = local favorito) ───────────────────
    exp_margin = exp_home - exp_away
    handicap = {}
    for line in SPREAD_LINES:
        # P(margen_local + line > 0): el local cubre el hándicap 'line'
        p_cover = 1.0 - _phi(((-line) - exp_margin) / margin_std)
        sign = f"{line:+.1f}"
        handicap[f"home_{sign}"] = round(p_cover * 100, 1)
        handicap[f"away_{(-line):+.1f}"] = round((1.0 - p_cover) * 100, 1)

    return {
        "sport": "nba",
        "home_team": home,
        "away_team": away,
        "model": "NBA Elo v1",
        "probabilities": {
            "home_win": round(p_home * 100, 1),
            "away_win": round(p_away * 100, 1),
        },
        "elo": {"home": round(elo_h, 1), "away": round(elo_a, 1),
                "matched_home": hk, "matched_away": ak},
        "expected_points": {
            "home":  round(exp_home, 1),
            "away":  round(exp_away, 1),
            "total": round(exp_total, 1),
            "margin": round(exp_margin, 1),
        },
        "over_under": over_under,
        "handicap": handicap,
        "meta": {
            "scoring_season": meta.get("scoring_season"),
            "has_home_stats": bool(sh),
            "has_away_stats": bool(sa),
        },
    }
