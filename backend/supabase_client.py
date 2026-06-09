"""
supabase_client.py
==================
Cliente Supabase compartido para toda la app.
Guarda y consulta predicciones.
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

_client: Client | None = None

def get_client() -> Client | None:
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_SECRET_KEY", "")
        if url and key:
            try:
                _client = create_client(url, key)
            except Exception as e:
                print(f"[Supabase] Error al conectar: {e}")
    return _client


def save_prediction(data: dict) -> dict | None:
    """
    Guarda una predicción en Supabase.
    Retorna el registro insertado (con su id) o None si falla.
    """
    sb = get_client()
    if not sb:
        return None
    try:
        result = sb.table("predictions").insert(data).execute()
        if result.data:
            print(f"[Supabase] Prediccion guardada id={result.data[0]['id']}")
            return result.data[0]
    except Exception as e:
        print(f"[Supabase] Error guardando prediccion: {e}")
    return None


def update_result(prediction_id: int, home_goals: int, away_goals: int) -> dict | None:
    """
    Actualiza el resultado real de una predicción.
    El trigger de Supabase calcula was_correct automáticamente.
    """
    sb = get_client()
    if not sb:
        return None

    # Determinar ganador real
    if home_goals > away_goals:
        result_actual = "Local"
    elif away_goals > home_goals:
        result_actual = "Visitante"
    else:
        result_actual = "Empate"

    try:
        result = sb.table("predictions").update({
            "result_home_goals": home_goals,
            "result_away_goals": away_goals,
            "result_actual":     result_actual,
        }).eq("id", prediction_id).execute()
        if result.data:
            rec = result.data[0]
            print(f"[Supabase] Resultado actualizado id={prediction_id} | correcto={rec.get('was_correct')}")
            return rec
    except Exception as e:
        print(f"[Supabase] Error actualizando resultado: {e}")
    return None


def get_predictions(limit: int = 50, offset: int = 0) -> list[dict]:
    """Retorna las predicciones más recientes."""
    sb = get_client()
    if not sb:
        return []
    try:
        result = (sb.table("predictions")
                    .select("*")
                    .order("created_at", desc=True)
                    .limit(limit)
                    .offset(offset)
                    .execute())
        return result.data or []
    except Exception as e:
        print(f"[Supabase] Error leyendo predicciones: {e}")
        return []


def get_stats() -> dict:
    """Retorna estadísticas globales de precisión."""
    sb = get_client()
    if not sb:
        return {}
    try:
        # Total predicciones
        total_res = sb.table("predictions").select("id", count="exact").execute()
        total = total_res.count or 0

        # Con resultado real
        evaluated_res = (sb.table("predictions")
                           .select("id", count="exact")
                           .not_.is_("result_actual", "null")
                           .execute())
        evaluated = evaluated_res.count or 0

        # Correctas
        correct_res = (sb.table("predictions")
                         .select("id", count="exact")
                         .eq("was_correct", True)
                         .execute())
        correct = correct_res.count or 0

        accuracy = round(correct / evaluated * 100, 1) if evaluated > 0 else None

        # Por liga
        by_league: dict = {}
        if evaluated > 0:
            rows = (sb.table("predictions")
                      .select("league, was_correct")
                      .not_.is_("result_actual", "null")
                      .execute()).data or []
            for row in rows:
                league = row.get("league") or "Desconocida"
                if league not in by_league:
                    by_league[league] = {"total": 0, "correct": 0}
                by_league[league]["total"] += 1
                if row.get("was_correct"):
                    by_league[league]["correct"] += 1

        return {
            "total_predictions": total,
            "evaluated":         evaluated,
            "correct":           correct,
            "accuracy":          accuracy,
            "pending":           total - evaluated,
            "by_league":         by_league,
        }
    except Exception as e:
        print(f"[Supabase] Error calculando stats: {e}")
        return {}
