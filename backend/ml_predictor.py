"""
ml_predictor.py — Predicción en producción usando el modelo XGBoost entrenado.

Se carga una sola vez en memoria. Si el modelo no existe, devuelve None
y predictor.py cae automáticamente al modelo por reglas.
"""
import os
import numpy as np

MODEL_PATH = os.path.join(os.path.dirname(__file__), "ml", "model.pkl")

_meta  = None   # dict con model, features, labels, accuracy
_ready = None   # True / False (None = no intentado todavía)

FEATURES = [
    "home_wins_5",    "home_draws_5",    "home_losses_5",
    "home_gf_5",      "home_ga_5",
    "away_wins_5",    "away_draws_5",    "away_losses_5",
    "away_gf_5",      "away_ga_5",
    "home_home_wins", "home_home_draws", "home_home_losses",
    "away_away_wins", "away_away_draws", "away_away_losses",
    "h2h_home_ratio", "h2h_draw_ratio",
]


def _load():
    global _meta, _ready
    if _ready is not None:
        return _ready
    try:
        import joblib
        _meta  = joblib.load(MODEL_PATH)
        _ready = True
        acc = _meta.get("accuracy", 0)
        print(f"[ML] Modelo XGBoost cargado — precisión histórica: {acc:.1%}")
    except Exception as e:
        _ready = False
        print(f"[ML] Modelo no disponible ({e}). Usando reglas.")
    return _ready


# ─── Feature extraction ──────────────────────────────────────────────────────

def _winrate_split(recent: list, as_home: bool) -> tuple:
    """Wins / draws / losses filtrando por was_home."""
    filtered = [m for m in recent if m.get("was_home") == as_home]
    if not filtered:
        return 1, 1, 1   # neutro
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
        probs    = model.predict_proba(np.array([features]))[0]  # [p_home, p_draw, p_away]

        # Las clases 0=local, 1=empate, 2=visitante
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
