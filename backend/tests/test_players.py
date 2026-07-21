"""
Tests de la lógica de goleadores en supabase_client.py (sin llamadas a la base).

Cubren get_top_scorers (orden y límite) y search_players (subcadena y longitud
mínima), inyectando el cache en memoria para no depender de Supabase.
"""

import supabase_client as sbc


def _player(name, goals, nat="X"):
    """Construye un jugador mínimo para los tests."""
    return {
        "name": name,
        "national_team": nat,
        "current_club": None,
        "position": None,
        "goals": goals,
        "penalties": 0,
        "own_goals": 0,
        "matches_scored": None,
        "first_year": 2000,
        "last_year": 2026,
    }


def _seed(players):
    """Ordena e inyecta el cache como lo hace _load_players()."""
    sbc._players_cache = sorted(players, key=lambda p: p["goals"], reverse=True)


def test_top_scorers_orden_y_limite():
    """Uso esperado: devuelve los N con más goles, ordenados desc."""
    _seed([_player("A", 10), _player("B", 30), _player("C", 20)])
    top = sbc.get_top_scorers(2)
    assert [p["name"] for p in top] == ["B", "C"]


def test_search_ignora_query_corta():
    """Caso límite: una query de menos de 2 caracteres no busca nada."""
    _seed([_player("Messi", 71)])
    assert sbc.search_players("m") == []


def test_search_sin_coincidencias():
    """Caso de fallo: sin coincidencias devuelve lista vacía."""
    _seed([_player("Messi", 71), _player("Ronaldo", 124)])
    assert sbc.search_players("zzz") == []


def test_search_encuentra_subcadena_case_insensitive():
    """Uso esperado: encuentra por subcadena sin distinguir mayúsculas."""
    _seed([_player("Lionel Messi", 71), _player("Cristiano Ronaldo", 124)])
    names = [p["name"] for p in sbc.search_players("MESS")]
    assert names == ["Lionel Messi"]
