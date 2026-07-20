"""
Tests de la lógica pura de supabase_client.py (sin llamadas a la base de datos).

Cubren la deduplicación del feed público de predicciones.
"""

import supabase_client as sbc


def _row(home, away, date, rid):
    """Construye una fila mínima de predicción para los tests."""
    return {"home_team": home, "away_team": away, "match_date": date, "id": rid}


def test_dedupe_keeps_one_per_match():
    """Uso esperado: el mismo partido (mismos equipos y fecha) aparece una vez."""
    rows = [
        _row("Real Madrid", "Barcelona", "2026-06-20", 3),  # más reciente
        _row("Real Madrid", "Barcelona", "2026-06-20", 2),  # duplicado
        _row("Liverpool", "City", "2026-06-21", 1),
    ]
    out = sbc._dedupe_matches(rows, limit=10)
    assert len(out) == 2
    # Conserva la primera ocurrencia (la más reciente, id=3)
    assert out[0]["id"] == 3
    assert out[1]["id"] == 1


def test_dedupe_is_case_insensitive():
    """Caso límite: diferencias de mayúsculas/espacios no rompen la dedup."""
    rows = [
        _row("Real Madrid", "Barcelona", "2026-06-20", 2),
        _row("  real madrid ", "BARCELONA", "2026-06-20", 1),
    ]
    out = sbc._dedupe_matches(rows, limit=10)
    assert len(out) == 1


def test_dedupe_respects_limit():
    """Caso de fallo: nunca devuelve más partidos que el límite pedido."""
    rows = [_row(f"A{i}", f"B{i}", "2026-06-20", i) for i in range(20)]
    out = sbc._dedupe_matches(rows, limit=10)
    assert len(out) == 10


def test_dedupe_empty():
    """Caso límite: lista vacía devuelve lista vacía."""
    assert sbc._dedupe_matches([], limit=10) == []
