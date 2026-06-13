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


def update_result(prediction_id: int, home_goals: int, away_goals: int,
                  corners: int | None = None, yellow_cards: int | None = None,
                  fouls: int | None = None) -> dict | None:
    """
    Actualiza el resultado real de una predicción.
    El trigger de Supabase calcula was_correct automáticamente.
    corners / yellow_cards / fouls son opcionales (best-effort vía API-Sports).
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

    payload = {
        "result_home_goals": home_goals,
        "result_away_goals": away_goals,
        "result_actual":     result_actual,
    }
    if corners is not None:
        payload["result_corners"] = corners
    if yellow_cards is not None:
        payload["result_yellow_cards"] = yellow_cards
    if fouls is not None:
        payload["result_fouls"] = fouls

    try:
        result = sb.table("predictions").update(payload).eq("id", prediction_id).execute()
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


def get_market_stats() -> dict:
    """
    Precisión del modelo desglosada por tipo de mercado.

    - 1X2, Over/Under 2.5 y BTTS: se evalúan con el marcador real (gratis).
    - Córners y tarjetas: error medio (MAE) entre lo esperado y lo real,
      solo donde hay datos reales capturados vía API-Sports.
    """
    sb = get_client()
    if not sb:
        return {}
    try:
        rows = (sb.table("predictions")
                  .select("pred_winner, result_actual, was_correct, markets_json, "
                          "result_home_goals, result_away_goals, "
                          "result_corners, result_yellow_cards, result_fouls")
                  .not_.is_("result_actual", "null")
                  .execute()).data or []
    except Exception as e:
        print(f"[Supabase] Error en market stats: {e}")
        return {}

    def acc(c: int, n: int):
        return round(c / n * 100, 1) if n else None

    # ── 1X2 ──────────────────────────────────────────────────────────────
    x12_n = sum(1 for r in rows if r.get("was_correct") is not None)
    x12_c = sum(1 for r in rows if r.get("was_correct"))

    # ── Over/Under 2.5 y BTTS (derivados del marcador) ───────────────────
    ou_n = ou_c = btts_n = btts_c = 0
    # ── Córners / tarjetas (error medio) ─────────────────────────────────
    cor_err: list[float] = []
    cor_line_n = cor_line_c = 0
    yel_err: list[float] = []
    yel_line_n = yel_line_c = 0

    for r in rows:
        hg, ag = r.get("result_home_goals"), r.get("result_away_goals")
        mk = r.get("markets_json") or {}

        if hg is not None and ag is not None:
            total_goals = hg + ag
            ou = mk.get("over_under", {}) or {}
            p_over = ou.get("over_2.5")
            if p_over is not None:
                ou_n += 1
                pred_over = p_over >= 50
                real_over = total_goals > 2.5
                if pred_over == real_over:
                    ou_c += 1

            p_btts = mk.get("btts_yes")
            if p_btts is not None:
                btts_n += 1
                pred_yes = p_btts >= 50
                real_yes = hg > 0 and ag > 0
                if pred_yes == real_yes:
                    btts_c += 1

        rc = r.get("result_corners")
        ec = mk.get("corners_expected")
        if rc is not None and ec is not None:
            cor_err.append(abs(rc - ec))
            cor_line_n += 1
            if (ec > 9.5) == (rc > 9.5):
                cor_line_c += 1

        ry = r.get("result_yellow_cards")
        ey = mk.get("yellow_cards_expected")
        if ry is not None and ey is not None:
            yel_err.append(abs(ry - ey))
            yel_line_n += 1
            if (ey > 3.5) == (ry > 3.5):
                yel_line_c += 1

    mae = lambda lst: round(sum(lst) / len(lst), 2) if lst else None

    return {
        "result_1x2":  {"n": x12_n, "accuracy": acc(x12_c, x12_n)},
        "over_under_25": {"n": ou_n, "accuracy": acc(ou_c, ou_n)},
        "btts":        {"n": btts_n, "accuracy": acc(btts_c, btts_n)},
        "corners":     {"n": cor_line_n, "line_9_5_accuracy": acc(cor_line_c, cor_line_n),
                        "avg_error": mae(cor_err)},
        "yellow_cards": {"n": yel_line_n, "line_3_5_accuracy": acc(yel_line_c, yel_line_n),
                        "avg_error": mae(yel_err)},
    }
