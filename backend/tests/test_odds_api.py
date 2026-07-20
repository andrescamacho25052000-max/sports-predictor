"""
Tests de odds_api.py — cuotas reales y cálculo de valor esperado (EV).

Cubren la lógica pura (sin llamadas de red): EV, extracción de mejores cuotas,
mapeo de ligas y anotación con probabilidades del modelo.
"""

import odds_api


# ── expected_value ───────────────────────────────────────────────────────────

def test_expected_value_positive():
    """Uso esperado: cuota mayor a la justa → EV positivo (hay valor)."""
    # Prob 60% → cuota justa 1.667. A 1.80 hay valor.
    ev = odds_api.expected_value(60.0, 1.80)
    assert ev > 0
    assert ev == round(0.60 * 1.80 - 1.0, 4)


def test_expected_value_negative_edge():
    """Caso límite: cuota por debajo de la justa → EV negativo (sin valor)."""
    # Prob 60% → cuota justa 1.667. A 1.50 no hay valor.
    assert odds_api.expected_value(60.0, 1.50) < 0


def test_expected_value_clamps_probability():
    """Caso de fallo: probabilidades fuera de rango no rompen el cálculo."""
    # 150% se trata como 100%; -10% como 0%.
    assert odds_api.expected_value(150.0, 2.0) == round(1.0 * 2.0 - 1.0, 4)
    assert odds_api.expected_value(-10.0, 2.0) == -1.0


# ── sport_key_for ────────────────────────────────────────────────────────────

def test_sport_key_known_league():
    assert odds_api.sport_key_for("La Liga") == "soccer_spain_la_liga"


def test_sport_key_unknown_league():
    """Liga sin mapeo devuelve None (degrada sin error)."""
    assert odds_api.sport_key_for("Liga Inventada") is None


# ── _best_h2h ────────────────────────────────────────────────────────────────

def _bookmakers_h2h():
    return [
        {"markets": [{"key": "h2h", "outcomes": [
            {"name": "Real Madrid", "price": 1.80},
            {"name": "Draw",        "price": 3.40},
            {"name": "Barcelona",   "price": 4.10},
        ]}]},
        {"markets": [{"key": "h2h", "outcomes": [
            {"name": "Real Madrid", "price": 1.85},  # mejor para local
            {"name": "Draw",        "price": 3.30},
            {"name": "Barcelona",   "price": 4.50},   # mejor para visitante
        ]}]},
    ]


def test_best_h2h_picks_best_across_bookmakers():
    """Uso esperado: toma la mejor (más alta) cuota de cada resultado."""
    best = odds_api._best_h2h(_bookmakers_h2h(), "Real Madrid", "Barcelona")
    assert best == {"home": 1.85, "draw": 3.40, "away": 4.50}


def test_best_h2h_no_market_returns_none():
    """Caso de fallo: sin mercado h2h devuelve None."""
    assert odds_api._best_h2h([{"markets": []}], "A", "B") is None


# ── _best_totals ─────────────────────────────────────────────────────────────

def test_best_totals_groups_by_line():
    bookmakers = [
        {"markets": [{"key": "totals", "outcomes": [
            {"name": "Over",  "point": 2.5, "price": 1.90},
            {"name": "Under", "point": 2.5, "price": 1.95},
        ]}]},
        {"markets": [{"key": "totals", "outcomes": [
            {"name": "Over",  "point": 2.5, "price": 2.00},  # mejor over
        ]}]},
    ]
    totals = odds_api._best_totals(bookmakers)
    assert totals["2.5"]["over"] == 2.00
    assert totals["2.5"]["under"] == 1.95


# ── annotate_markets ─────────────────────────────────────────────────────────

def test_annotate_markets_flags_value():
    """Uso esperado: combina cuotas + probabilidades y marca value/EV."""
    raw = {
        "h2h": {"home": 1.80, "draw": 3.40, "away": 4.50},
        "totals": {"2.5": {"over": 2.00, "under": 1.80}},
        "bookmaker_count": 2,
        "commence_time": "2026-06-15T18:00:00Z",
    }
    probs = {"home_win": 60.0, "draw": 25.0, "away_win": 15.0}
    poisson = {"over_under": {"over_2.5": 55.0, "under_2.5": 45.0}}

    out = odds_api.annotate_markets(raw, probs, poisson)
    assert out is not None
    # Local: 60% a 1.80 → EV positivo
    assert out["markets"]["1"]["value"] is True
    # Visitante: 15% a 4.50 → EV negativo
    assert out["markets"]["2"]["value"] is False
    # Over 2.5: 55% a 2.00 → EV positivo
    assert out["markets"]["over_2.5"]["value"] is True
    # best_value ordenado por EV descendente y solo con valor
    assert all(m["value"] for m in out["best_value"])
    assert out["best_value"] == sorted(out["best_value"], key=lambda m: m["ev"], reverse=True)


def test_annotate_markets_none_when_no_odds():
    """Caso de fallo: sin cuotas crudas devuelve None."""
    assert odds_api.annotate_markets(None, {"home_win": 50}, None) is None


# ── get_match_odds (sin API key) ─────────────────────────────────────────────

def test_get_match_odds_no_key(monkeypatch):
    """Caso de fallo: sin ODDS_API_KEY no llama a red y devuelve None."""
    monkeypatch.setattr(odds_api, "API_KEY", "")
    assert odds_api.get_match_odds("Real Madrid", "Barcelona", "La Liga") is None
