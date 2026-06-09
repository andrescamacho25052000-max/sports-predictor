"""
ml_predictor.py — Predicción en producción usando el modelo XGBoost entrenado.

Se carga una sola vez en memoria. Si el modelo no existe, devuelve None
y predictor.py cae automáticamente al modelo por reglas.

v2: incluye Elo rating y points-per-game como features adicionales.
"""
import os
import numpy as np

MODEL_PATH    = os.path.join(os.path.dirname(__file__), "ml", "model.pkl")
ELO_PATH      = os.path.join(os.path.dirname(__file__), "ml", "data", "elo_ratings.json")

_meta  = None   # dict con model, features, labels, accuracy
_ready = None   # True / False (None = no intentado todavía)
_elo: dict[int, float] = {}   # team_id → elo rating (cargado desde JSON)

BASE_ELO = 1500
HOME_ADV = 100

FEATURES = [
    "home_wins_5",       "home_draws_5",       "home_losses_5",
    "home_gf_5",         "home_ga_5",
    "away_wins_5",       "away_draws_5",       "away_losses_5",
    "away_gf_5",         "away_ga_5",
    "home_home_wins",    "home_home_draws",    "home_home_losses",
    "away_away_wins",    "away_away_draws",    "away_away_losses",
    "h2h_home_ratio",    "h2h_draw_ratio",
    "elo_diff",          "elo_home_expected",
    "home_pts_per_game", "away_pts_per_game",
]


def _load():
    global _meta, _ready, _elo
    if _ready is not None:
        return _ready
    try:
        import joblib, json
        _meta  = joblib.load(MODEL_PATH)
        _ready = True
        acc = _meta.get("accuracy", 0)
        print(f"[ML] Modelo XGBoost cargado — precisión histórica: {acc:.1%}")
    except Exception as e:
        _ready = False
        print(f"[ML] Modelo no disponible ({e}). Usando reglas.")
        return _ready

    # Cargar ratings Elo
    try:
        import json
        with open(ELO_PATH, encoding="utf-8") as f:
            raw = json.load(f)
        _elo = {int(k): float(v) for k, v in raw.items()}
        print(f"[ML] Elo cargado: {len(_elo)} equipos")
    except Exception as e:
        print(f"[ML] Elo no disponible ({e}). Usando valores neutros.")

    return _ready


def _get_elo(team_id: int | None) -> float:
    if team_id is None:
        return BASE_ELO
    return _elo.get(team_id, BASE_ELO)


def _elo_features(home_id: int | None, away_id: int | None) -> tuple[float, float]:
    """(elo_diff, elo_home_expected)"""
    h_elo = _get_elo(home_id)
    a_elo = _get_elo(away_id)
    diff  = h_elo - a_elo
    exp   = 1 / (1 + 10 ** ((a_elo - (h_elo + HOME_ADV)) / 400))
    return diff, exp


# ─── Feature extraction ──────────────────────────────────────────────────────

def _winrate_split(recent: list, as_home: bool) -> tuple:
    """Wins / draws / losses filtrando por was_home."""
    filtered = [m for m in recent if m.get("was_home") == as_home]
    if not filtered:
        return 1, 1, 1
    w = sum(1 for m in filtered if m.get("result") == "V")
    d = sum(1 for m in filtered if m.get("result") == "E")
    l = len(filtered) - w - d
    return w, d, l


def _extract(home_stats: dict, away_stats: dict, h2h_data: dict | None) -> list:
    hr = home_stats.get("recent_matches", [])
    ar = away_stats.get("recent_matches", [])

    h_hw, h_hd, h_hl = _winrate_split(hr[:3], as_home=True)
    a_aw, a_ad, a_al = _winrate_split(ar[:3], as_home=False)

    if h2h_data and h2h_data.get("total", 0) > 0:
        t = h2h_data["total"]
        h2h_hr = h2h_data["wins"]  / t
        h2h_dr = h2h_data["draws"] / t
    else:
        h2h_hr, h2h_dr = 0.45, 0.27

    # Elo features (usa team_id si está disponible)
    home_id = home_stats.get("team_id") or home_stats.get("id")
    away_id = away_stats.get("team_id") or away_stats.get("id")
    elo_diff, elo_home_exp = _elo_features(home_id, away_id)

    # Points per game (si vienen en stats, sino neutral)
    home_ppg = home_stats.get("pts_per_game", 1.0)
    away_ppg = away_stats.get("pts_per_game", 1.0)

    return [
        home_stats.get("wins_last5",          2),
        home_stats.get("draws_last5",         1),
        home_stats.get("losses_last5",        2),
        home_stats.get("goals_scored_last5",  6),
        home_stats.get("goals_conceded_last5",6),
        away_stats.get("wins_last5",          2),
        away_stats.get("draws_last5",         1),
        away_stats.get("losses_last5",        2),
        away_stats.get("goals_scored_last5",  6),
        away_stats.get("goals_conceded_last5",6),
        h_hw, h_hd, h_hl,
        a_aw, a_ad, a_al,
        h2h_hr, h2h_dr,
        elo_diff, elo_home_exp,
        home_ppg, away_ppg,
    ]


# ─── Predicción ──────────────────────────────────────────────────────────────

def predict_ml(
    home_stats: dict,
    away_stats:  dict,
    h2h_data:    dict | None,
) -> dict | None:
    """
    Devuelve {"home_win": float%, "draw": float%, "away_win": float%}
    o None si el modelo no está disponible.
    """
    if not _load():
        return None
    if not home_stats or not away_stats:
        return None

    try:
        features = _extract(home_stats, away_stats, h2h_data)
        model    = _meta["model"]

        # Compatibilidad: si el modelo fue entrenado con 18 features (v1),
        # recortamos a las primeras 18 para no romper predicciones en producción.
        expected_n = len(_meta.get("features", FEATURES))
        if expected_n < len(features):
            features = features[:expected_n]

        probs    = model.predict_proba(np.array([features]))[0]
        classes  = list(model.classes_)
        p        = {c: float(probs[i]) for i, c in enumerate(classes)}

        return {
            "home_win": round(p.get(0, 0.34) * 100, 1),
            "draw":     round(p.get(1, 0.27) * 100, 1),
            "away_win": round(p.get(2, 0.39) * 100, 1),
        }
    except Exception as e:
        print(f"[ML] Error en inferencia: {e}")
        return None


def model_accuracy() -> float | None:
    """Precisión del modelo (para mostrar en la UI si se desea)."""
    if _ready and _meta:
        return _meta.get("accuracy")
    return None
