"""
result_checker.py
=================
Consulta automáticamente los resultados reales de los partidos predichos.

Flujo:
  1. Obtiene predicciones pendientes (sin resultado) cuya fecha ya pasó.
  2. Para cada una, busca el partido en football-data.org usando fd_home_id / fd_away_id.
     Si no hay IDs guardados, intenta buscar por nombre de equipo y fecha.
  3. Si el partido terminó (FINISHED), guarda el resultado real.
  4. El trigger de Supabase calcula was_correct automáticamente.

Se llama desde main.py vía asyncio (cada hora en segundo plano).
"""

import os
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import supabase_client as sbc
import api_sports as asports

load_dotenv()

FD_KEY = os.getenv("FOOTBALL_API_KEY", "")
FD_BASE = "https://api.football-data.org/v4"
HEADERS = {"X-Auth-Token": FD_KEY}


# ── Caché de nombre → ID de equipo (evita llamadas repetidas) ────────────────
_team_id_cache: dict[str, int | None] = {}

def _resolve_team_id(name: str) -> int | None:
    """Busca el team_id en football-data.org por nombre."""
    if name in _team_id_cache:
        return _team_id_cache[name]
    try:
        res = requests.get(f"{FD_BASE}/teams", headers=HEADERS,
                           params={"name": name}, timeout=8)
        if res.status_code == 200:
            teams = res.json().get("teams", [])
            if teams:
                tid = teams[0]["id"]
                _team_id_cache[name] = tid
                return tid
    except Exception:
        pass
    _team_id_cache[name] = None
    return None


def _fetch_match_result(home_id: int | None, away_id: int | None,
                        match_date: str, home_name: str, away_name: str) -> dict | None:
    """
    Busca el partido en football-data.org.
    Retorna {"home_goals": int, "away_goals": int} si está FINISHED, None si no.
    """
    try:
        # Ventana de búsqueda: ±1 día de la fecha del partido
        dt = datetime.fromisoformat(match_date)
        date_from = (dt - timedelta(days=1)).strftime("%Y-%m-%d")
        date_to   = (dt + timedelta(days=1)).strftime("%Y-%m-%d")

        # Intentar con home_id si está disponible
        if home_id:
            res = requests.get(
                f"{FD_BASE}/teams/{home_id}/matches",
                headers=HEADERS,
                params={"status": "FINISHED", "dateFrom": date_from, "dateTo": date_to},
                timeout=10,
            )
            if res.status_code == 200:
                for m in res.json().get("matches", []):
                    away = m.get("awayTeam", {})
                    if away_id and away.get("id") == away_id:
                        score = m["score"]["fullTime"]
                        return {"home_goals": score["home"], "away_goals": score["away"]}
                    # fallback: comparar por nombre
                    if away_name.lower() in (away.get("name") or "").lower():
                        score = m["score"]["fullTime"]
                        return {"home_goals": score["home"], "away_goals": score["away"]}

        # Si no hay IDs, buscar por nombre (más lento, pero funciona)
        if not home_id:
            hid = _resolve_team_id(home_name)
            if hid:
                return _fetch_match_result(hid, away_id, match_date, home_name, away_name)

    except Exception as e:
        print(f"[ResultChecker] Error consultando partido {home_name} vs {away_name}: {e}")
    return None


def check_and_update_pending() -> int:
    """
    Revisa predicciones pendientes y actualiza las que ya tienen resultado.
    Retorna la cantidad de predicciones actualizadas.
    """
    sb = sbc.get_client()
    if not sb:
        print("[ResultChecker] Supabase no disponible")
        return 0

    now_utc = datetime.now(timezone.utc)
    # Solo buscar partidos cuya fecha ya pasó (al menos 2 horas de margen)
    cutoff = (now_utc - timedelta(hours=2)).strftime("%Y-%m-%d")

    try:
        rows = (sb.table("predictions")
                  .select("id, home_team, away_team, match_date, fd_home_id, fd_away_id")
                  .is_("result_actual", "null")          # sin resultado
                  .lte("match_date", cutoff)             # fecha ya pasó
                  .not_.is_("match_date", "null")        # tienen fecha
                  .limit(20)
                  .execute()).data or []
    except Exception as e:
        print(f"[ResultChecker] Error consultando pendientes: {e}")
        return 0

    if not rows:
        print("[ResultChecker] No hay predicciones pendientes de resultado")
        return 0

    print(f"[ResultChecker] Verificando {len(rows)} predicciones pendientes...")

    updated = 0

    for row in rows:
        pid        = row["id"]
        home_name  = row["home_team"]
        away_name  = row["away_team"]
        match_date = row["match_date"]
        home_id    = row.get("fd_home_id")
        away_id    = row.get("fd_away_id")

        result = _fetch_match_result(home_id, away_id, match_date, home_name, away_name)

        if result:
            # Best-effort: estadísticas reales (córners/tarjetas/faltas) vía API-Sports.
            # Si la cuota está agotada o no se encuentra, se guarda solo el marcador.
            stats = None
            try:
                stats = asports.get_fixture_stats(home_name, away_name, match_date)
            except Exception as e:
                print(f"[ResultChecker] Sin stats de API-Sports para #{pid}: {e}")

            ok = sbc.update_result(
                pid, result["home_goals"], result["away_goals"],
                corners=(stats or {}).get("corners"),
                yellow_cards=(stats or {}).get("yellow_cards"),
                fouls=(stats or {}).get("fouls"),
            )
            if ok:
                # Marcar como actualizado automáticamente
                try:
                    sb.table("predictions").update({"auto_updated": True}).eq("id", pid).execute()
                except Exception:
                    pass
                print(f"[ResultChecker] ✓ #{pid} {home_name} {result['home_goals']}-{result['away_goals']} {away_name}")
                updated += 1
        else:
            print(f"[ResultChecker] Sin resultado aún: #{pid} {home_name} vs {away_name} ({match_date})")

    # ── Reentrenar si llegaron nuevos resultados ───────────────────────────
    if updated > 0:
        print(f"[ResultChecker] {updated} resultado(s) nuevos → disparando reentrenamiento...")
        try:
            import sys, os
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ml"))
            from ml.incremental_trainer import run_incremental_training
            train_result = run_incremental_training()
            if train_result.get("status") == "trained":
                v   = train_result.get("new_version")
                acc = train_result.get("accuracy_after")
                imp = train_result.get("improvement")
                imp_str = f" (+{imp}%)" if imp and imp > 0 else ""
                print(f"[ResultChecker] Modelo actualizado v{v} | accuracy en nuevos datos: {acc}%{imp_str}")
            else:
                print(f"[ResultChecker] Reentrenamiento: {train_result.get('message', train_result.get('status'))}")
        except Exception as e:
            print(f"[ResultChecker] Error en reentrenamiento: {e}")

    return updated


# ── Para prueba manual ────────────────────────────────────────────────────────
if __name__ == "__main__":
    n = check_and_update_pending()
    print(f"\n[ResultChecker] {n} predicciones actualizadas")
