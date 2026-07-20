"""
Tests de la autorización de main._resolve_user (resolución de usuario/admin).

Se monkeypatchea supabase_client.get_user_from_token para no depender de la red.
"""

import main


def test_resolve_anonymous_no_header():
    """Sin header Authorization → usuario anónimo, no admin."""
    u = main._resolve_user(None)
    assert u == {"id": None, "email": None, "is_admin": False}


def test_resolve_anonymous_bad_scheme(monkeypatch):
    """Header sin 'Bearer ' → anónimo (no se intenta validar)."""
    u = main._resolve_user("Basic abc")
    assert u["id"] is None and u["is_admin"] is False


def test_resolve_normal_user(monkeypatch):
    """Token válido de usuario normal → id resuelto, is_admin False."""
    monkeypatch.setattr(main.sbc, "get_user_from_token",
                        lambda t: {"id": "u-123", "email": "user@example.com"})
    monkeypatch.setattr(main, "_ADMIN_EMAILS", {"admin@example.com"})
    u = main._resolve_user("Bearer validtoken")
    assert u["id"] == "u-123"
    assert u["is_admin"] is False


def test_resolve_admin_user(monkeypatch):
    """Token válido cuyo email está en ADMIN_EMAILS → is_admin True."""
    monkeypatch.setattr(main.sbc, "get_user_from_token",
                        lambda t: {"id": "a-1", "email": "Admin@Example.com"})
    monkeypatch.setattr(main, "_ADMIN_EMAILS", {"admin@example.com"})
    u = main._resolve_user("Bearer validtoken")
    assert u["is_admin"] is True  # comparación case-insensitive


def test_resolve_invalid_token(monkeypatch):
    """Token inválido (get_user_from_token devuelve None) → anónimo."""
    monkeypatch.setattr(main.sbc, "get_user_from_token", lambda t: None)
    u = main._resolve_user("Bearer garbage")
    assert u["id"] is None and u["is_admin"] is False
