"""
Tests de ml/dixon_coles.py — prediccion 1X2 y utilidades (sin ajuste real).
"""

from ml import dixon_coles as dc
import ensemble


def _params():
    # Equipo A claramente mas fuerte que B (mejor ataque y defensa).
    return {
        "teams": ["A", "B"],
        "att":   [0.5, -0.5],
        "dff":   [-0.2, 0.2],
        "mu":    0.2, "gamma": 0.25, "rho": -0.03,
    }


def test_predict_1x2_sums_to_one():
    pr = dc.predict_1x2(_params(), "A", "B")
    assert abs(sum(pr) - 1.0) < 1e-6


def test_predict_1x2_stronger_favored():
    """El equipo fuerte como local domina la probabilidad."""
    pr = dc.predict_1x2(_params(), "A", "B")
    assert pr[0] > pr[2]  # pH > pA


def test_predict_1x2_unknown_team():
    assert dc.predict_1x2(_params(), "A", "Z") is None


def test_match_team_partial():
    assert dc._match_team("real madrid", ["Real Madrid CF", "FC Barcelona"]) == "Real Madrid CF"
    assert dc._match_team("nadie", ["Real Madrid CF"]) is None


def test_predict_runtime(monkeypatch):
    """predict_runtime mapea liga->codigo y devuelve % planos."""
    monkeypatch.setattr(dc, "_params", {"PD": _params()})
    out = dc.predict_runtime("La Liga", "A", "B")
    assert out is not None
    assert abs(sum(out.values()) - 100.0) < 0.5
    assert isinstance(out["home_win"], float)
    # liga no mapeada -> None
    assert dc.predict_runtime("Liga Inexistente", "A", "B") is None


def test_predict_national(monkeypatch):
    """El modelo nacional predice si los equipos estan; None si no (p.ej. clubes)."""
    monkeypatch.setattr(dc, "_national", {**_params(), "teams": ["Argentina", "Brazil"]})
    out = dc.predict_national("Argentina", "Brazil")
    assert out is not None
    assert abs(sum(out.values()) - 100.0) < 0.5
    # equipo no nacional -> None (seguro de llamar en partidos de clubes)
    assert dc.predict_national("Real Madrid", "Barcelona") is None


def test_weighted_blend_favors_primary():
    """weighted_blend con peso alto se parece mas a la primaria."""
    dc_pred = {"home_win": 60.0, "draw": 20.0, "away_win": 20.0}
    ens = {"home_win": 30.0, "draw": 30.0, "away_win": 40.0}
    out = ensemble.weighted_blend(dc_pred, ens, w_primary=0.7)
    assert abs(sum(out.values()) - 100.0) < 0.5
    assert out["home_win"] > out["away_win"]  # domina la primaria (DC)
