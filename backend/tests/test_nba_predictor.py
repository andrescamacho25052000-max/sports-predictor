"""
Tests de nba_predictor.py — lógica pura de predicción NBA.

Se inyectan datos de modelo fijos (monkeypatch) para no depender de los JSON
construidos ni de la red.
"""

import nba_predictor as nba


# ── helpers numéricos ────────────────────────────────────────────────────────

def test_phi_known_values():
    assert abs(nba._phi(0.0) - 0.5) < 1e-9
    assert nba._phi(5.0) > 0.999
    assert nba._phi(-5.0) < 0.001


def test_win_prob_home_advantage():
    """Con Elo igual, el local supera el 50% por la ventaja de localía."""
    p = nba._win_prob(1500, 1500)
    assert 0.5 < p < 0.7


def test_win_prob_monotonic():
    """Más Elo local → más probabilidad de ganar."""
    assert nba._win_prob(1700, 1500) > nba._win_prob(1550, 1500)


def test_match_team_partial():
    table = {"Los Angeles Lakers": 1, "Boston Celtics": 1}
    assert nba._match_team("lakers", table) == "Los Angeles Lakers"
    assert nba._match_team("Boston Celtics", table) == "Boston Celtics"
    assert nba._match_team("Equipo Inexistente", table) is None


# ── predict (con modelo inyectado) ───────────────────────────────────────────

def _inject(monkeypatch):
    monkeypatch.setattr(nba, "_elo", {"Strong": 1700.0, "Weak": 1400.0})
    monkeypatch.setattr(nba, "_stats", {
        "Strong": {"pts_for_avg": 118.0, "pts_against_avg": 108.0, "logo": ""},
        "Weak":   {"pts_for_avg": 108.0, "pts_against_avg": 118.0, "logo": ""},
    })
    monkeypatch.setattr(nba, "_meta", {
        "league_avg_total": 226.0, "total_std": 21.0, "margin_std": 16.0,
        "home_margin_mean": 2.0, "scoring_season": "2024-2025",
    })


def test_predict_probabilities_sum_100(monkeypatch):
    """Uso esperado: las dos probabilidades (sin empate) suman ~100%."""
    _inject(monkeypatch)
    p = nba.predict("Strong", "Weak")
    total = p["probabilities"]["home_win"] + p["probabilities"]["away_win"]
    assert abs(total - 100.0) < 0.2


def test_predict_stronger_team_favored(monkeypatch):
    """El equipo más fuerte (local) tiene clara ventaja."""
    _inject(monkeypatch)
    p = nba.predict("Strong", "Weak")
    assert p["probabilities"]["home_win"] > 70
    assert p["expected_points"]["margin"] > 0  # local marca más


def test_predict_over_under_complementary(monkeypatch):
    """Caso límite: en cada línea, over + under = 100%."""
    _inject(monkeypatch)
    p = nba.predict("Strong", "Weak")
    for line, d in p["over_under"].items():
        assert abs(d["over"] + d["under"] - 100.0) < 0.2


def test_predict_unknown_team_uses_defaults(monkeypatch):
    """Caso de fallo: equipo sin datos → cae a promedios de liga (no crashea)."""
    _inject(monkeypatch)
    p = nba.predict("Strong", "Desconocido")
    assert p["meta"]["has_away_stats"] is False
    assert p["expected_points"]["total"] > 0
