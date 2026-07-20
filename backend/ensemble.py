"""
ensemble.py — Ensamble XGBoost + Poisson y calibracion por temperatura.

Mejora medida en backtest temporal (ml/tune_ensemble.py): mezclar el 1X2 del
XGBoost con el 1X2 del Poisson y calibrar baja el RPS y el log-loss frente al
XGBoost solo. Los pesos ganadores se leen de ml/data/ensemble_config.json; si el
archivo no existe (p.ej. en produccion sin rebuild), se usan los valores por
defecto ya calibrados.
"""

import json
import os

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "ml", "data", "ensemble_config.json")

# Valores por defecto (resultado del ultimo tune_ensemble sobre el holdout temporal)
DEFAULT_W = 0.6   # peso del XGBoost; el resto (0.4) es del Poisson
DEFAULT_T = 1.1   # temperatura de calibracion (>1 aplana, <1 agudiza)

_KEYS = ("home_win", "draw", "away_win")
_cfg: dict | None = None


def _load() -> dict:
    global _cfg
    if _cfg is None:
        _cfg = {"w_xgboost": DEFAULT_W, "temperature": DEFAULT_T}
        try:
            if os.path.exists(_CONFIG_PATH):
                d = json.loads(open(_CONFIG_PATH, encoding="utf-8").read())
                _cfg = {
                    "w_xgboost":   float(d.get("w_xgboost", DEFAULT_W)),
                    "temperature": float(d.get("temperature", DEFAULT_T)),
                }
        except Exception:
            pass
    return _cfg


def _norm(vals: list[float]) -> list[float]:
    s = sum(vals) or 1.0
    return [v / s for v in vals]


def blend_and_calibrate(xgb_pct: dict, poisson_1x2_pct: dict) -> dict:
    """Mezcla y calibra las probabilidades 1X2.

    Args:
        xgb_pct (dict): Probabilidades del modelo principal (home_win/draw/away_win) en %.
        poisson_1x2_pct (dict): Probabilidades 1X2 del Poisson en %.

    Returns:
        dict: Probabilidades finales (home_win/draw/away_win) en %, sumando ~100.
    """
    cfg = _load()
    w, T = cfg["w_xgboost"], cfg["temperature"]

    x = _norm([max(0.0, float(xgb_pct.get(k, 0))) for k in _KEYS])
    p = _norm([max(0.0, float(poisson_1x2_pct.get(k, 0))) for k in _KEYS])

    blended = _norm([w * xi + (1 - w) * pi for xi, pi in zip(x, p)])
    calibrated = _norm([max(v, 1e-9) ** (1.0 / T) for v in blended])

    return {k: round(v * 100, 1) for k, v in zip(_KEYS, calibrated)}


def weighted_blend(primary_pct: dict, secondary_pct: dict, w_primary: float = 0.7) -> dict:
    """Mezcla ponderada de dos predicciones 1X2 (en %).

    Se usa para combinar el modelo primario (Dixon-Coles) con el ensamble
    XGBoost+Poisson. Dixon-Coles pesa mas porque midio mejor en el backtest.

    Args:
        primary_pct (dict): Predicción dominante (home_win/draw/away_win en %).
        secondary_pct (dict): Predicción secundaria.
        w_primary (float): Peso de la primaria (0-1).

    Returns:
        dict: 1X2 combinado en %, sumando ~100.
    """
    a = _norm([max(0.0, float(primary_pct.get(k, 0))) for k in _KEYS])
    b = _norm([max(0.0, float(secondary_pct.get(k, 0))) for k in _KEYS])
    mix = _norm([w_primary * ai + (1 - w_primary) * bi for ai, bi in zip(a, b)])
    return {k: round(v * 100, 1) for k, v in zip(_KEYS, mix)}
