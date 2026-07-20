"""
Tests de ensemble.py — mezcla XGBoost + Poisson y calibracion.
"""

import ensemble


def test_blend_sums_100():
    """Uso esperado: las probabilidades finales suman ~100%."""
    xgb = {"home_win": 50.0, "draw": 30.0, "away_win": 20.0}
    poi = {"home_win": 40.0, "draw": 30.0, "away_win": 30.0}
    out = ensemble.blend_and_calibrate(xgb, poi)
    assert abs(sum(out.values()) - 100.0) < 0.5
    assert set(out) == {"home_win", "draw", "away_win"}


def test_blend_is_between_inputs():
    """El ensamble queda entre las dos senales (no fuera de rango)."""
    xgb = {"home_win": 70.0, "draw": 20.0, "away_win": 10.0}
    poi = {"home_win": 40.0, "draw": 30.0, "away_win": 30.0}
    out = ensemble.blend_and_calibrate(xgb, poi)
    # el favorito local sigue siendo el favorito, pero moderado por el Poisson
    assert 40.0 <= out["home_win"] <= 70.0
    assert out["home_win"] == max(out.values())


def test_blend_handles_zero_poisson(monkeypatch):
    """Caso de fallo: si el Poisson viene vacio no crashea."""
    out = ensemble.blend_and_calibrate(
        {"home_win": 50.0, "draw": 25.0, "away_win": 25.0},
        {"home_win": 0, "draw": 0, "away_win": 0},
    )
    assert abs(sum(out.values()) - 100.0) < 0.5


def test_weight_extremes(monkeypatch):
    """Con w=1 el resultado es casi el XGBoost puro (salvo calibracion)."""
    monkeypatch.setattr(ensemble, "_cfg", {"w_xgboost": 1.0, "temperature": 1.0})
    xgb = {"home_win": 60.0, "draw": 25.0, "away_win": 15.0}
    poi = {"home_win": 10.0, "draw": 10.0, "away_win": 80.0}
    out = ensemble.blend_and_calibrate(xgb, poi)
    assert abs(out["home_win"] - 60.0) < 0.5
