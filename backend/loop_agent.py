"""
loop_agent.py — Agente de seguimiento automático de predicciones deportivas.

Hace dos cosas cada vez que se ejecuta:
  1. PREDECIR: escanea partidos próximos en todas las ligas → guarda en Excel
  2. RESULTADOS: compara predicciones pasadas con resultados reales → actualiza Excel

Uso:
  python backend/loop_agent.py              ← ejecutar completo
  python backend/loop_agent.py --dry-run    ← simular sin guardar nada
  python backend/loop_agent.py --solo-pred  ← solo fase de predicciones
  python backend/loop_agent.py --solo-res   ← solo fase de resultados
"""
import sys
import os

# Asegurar que el backend está en el sys.path
sys.path.insert(0, os.path.dirname(__file__))

from datetime import date
from tracker import ExcelTracker
import football_api as fapi
import api_sports   as asports
import weather_api  as wapi
from predictor import predict

# ─── Configuración ───────────────────────────────────────────────────────────

EXCEL_PATH  = os.path.join(os.path.dirname(__file__), "..", "predicciones.xlsx")
DRY_RUN     = "--dry-run"   in sys.argv
SOLO_PRED   = "--solo-pred" in sys.argv
SOLO_RES    = "--solo-res"  in sys.argv

# Pon en False si estás cerca del límite diario de API-Sports (100 req/día)
USE_API_SPORTS = True


# ─── Utilidades ──────────────────────────────────────────────────────────────

def _banner(text: str):
    print(f"\n{'─' * 56}")
    print(f"  {text}")
    print(f"{'─' * 56}")


def _predict_match(match: dict, league: str) -> dict | None:
    """Genera la predicción completa para un partido usando todas las fuentes."""
    home       = match.get("home", "")
    away       = match.get("away", "")
    home_id    = match.get("home_id")
    away_id    = match.get("away_id")
    match_date = (match.get("date") or "")[:10]

    home_stats = away_stats = h2h_data = stadium_info = weather_info = None

    if home_id and away_id:
        # ── Football-Data.org ────────────────────────────────────────
        home_stats = fapi.get_team_stats(home, int(home_id), league)
        away_stats = fapi.get_team_stats(away, int(away_id), league)

        home_recent = fapi.get_team_recent_matches(int(home_id))
        away_recent = fapi.get_team_recent_matches(int(away_id))
        home_stats["recent_matches"] = home_recent
        away_stats["recent_matches"] = away_recent

        h2h_data = fapi.get_h2h(int(home_id), int(away_id))

        # ── API-Sports (lesionados + estadio) ────────────────────────
        if USE_API_SPORTS:
            home_info = asports.search_team(home)
            if home_info:
                home_injuries = asports.get_injuries(home_info["id"])
                home_stats["injured_players"] = len(home_injuries)
                stadium_info = home_info.get("venue", {})
                stadium_info["home_team_logo"] = home_info.get("logo", "")

            away_info = asports.search_team(away)
            if away_info:
                away_injuries = asports.get_injuries(away_info["id"])
                away_stats["injured_players"] = len(away_injuries)

        # ── Open-Meteo (clima) ───────────────────────────────────────
        if stadium_info and stadium_info.get("city") and match_date:
            weather_info = wapi.get_weather(stadium_info["city"], match_date)

    return predict(
        home, away,
        home_stats, away_stats,
        weather_info, stadium_info,
        h2h_data=h2h_data,
        match_date=match_date,
    )


# ─── Fase 1: Predecir partidos próximos ──────────────────────────────────────

def phase_predict(tracker: ExcelTracker):
    _banner("📅 FASE 1 — Predicciones de partidos próximos")
    nuevas = 0

    for league in fapi.get_leagues():
        matches = fapi.get_matches(league)
        for match in matches:
            home       = match.get("home", "")
            away       = match.get("away", "")
            match_date = (match.get("date") or "")[:10]

            if not home or not away or not match_date:
                continue
            if tracker.already_tracked(home, away, match_date):
                continue  # ya predicho en una ejecución anterior

            print(f"  ⚽ {home} vs {away}  [{match_date}]  ({league})")

            try:
                result = _predict_match(match, league)
                if not result:
                    print("     ⚠️  No se pudo generar predicción")
                    continue

                probs = result["probabilities"]
                print(
                    f"     → Local {probs['home_win']}%  "
                    f"Empate {probs['draw']}%  "
                    f"Visitante {probs['away_win']}%"
                )

                if not DRY_RUN:
                    tracker.add_prediction(match, result, league)
                nuevas += 1

            except Exception as exc:
                print(f"     ⚠️  Error: {exc}")

    if nuevas == 0:
        print("  (Sin partidos nuevos para predecir)")
    else:
        print(f"\n  ✅ {nuevas} predicci{'ón guardada' if nuevas == 1 else 'ones guardadas'}")


# ─── Fase 2: Actualizar resultados reales ────────────────────────────────────

def phase_results(tracker: ExcelTracker):
    _banner("🔍 FASE 2 — Resultados de partidos ya jugados")
    actualizados = 0

    pending = tracker.get_pending_past_matches()
    if not pending:
        print("  (Sin partidos pendientes de resultado)")
        return

    for item in pending:
        home    = item["home"]
        away    = item["away"]
        home_id = item.get("home_id")
        away_id = item.get("away_id")

        if not home_id or not away_id:
            print(f"  ⏭️  Sin IDs: {home} vs {away} — omitido")
            continue

        print(f"  🔍 {home} vs {away}  [{item['date']}]")

        try:
            result = fapi.get_match_result(int(home_id), int(away_id), item["date"])
        except Exception as exc:
            print(f"     ⚠️  Error al buscar resultado: {exc}")
            continue

        if not result:
            print("     ⏳ Resultado aún no disponible en la API")
            continue

        winner    = result["winner"]
        predicted = item["predicted"]
        icon      = "✅" if winner == predicted else "❌"
        print(
            f"     {icon}  {result['home_goals']}–{result['away_goals']}"
            f"  |  Pred: {predicted}  →  Real: {winner}"
        )

        if not DRY_RUN:
            tracker.update_result(
                item["row"],
                result["home_goals"],
                result["away_goals"],
                winner,
                predicted,
            )
        actualizados += 1

    if actualizados:
        print(f"\n  ✅ {actualizados} resultado{'s actualizados' if actualizados != 1 else ' actualizado'}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    _banner(
        f"🤖 SPORTS PREDICTOR — AUTO TRACKER"
        f"  {'[DRY RUN — nada se guarda]' if DRY_RUN else ''}"
    )
    print(f"  Fecha hoy: {date.today()}")
    print(f"  Excel:     {os.path.abspath(EXCEL_PATH)}")
    if DRY_RUN:
        print("  Modo DRY RUN activado — ningún cambio se escribirá")

    tracker = ExcelTracker(EXCEL_PATH)

    run_pred = not SOLO_RES
    run_res  = not SOLO_PRED

    if run_pred:
        phase_predict(tracker)

    if run_res:
        phase_results(tracker)

    # ── Resumen final ─────────────────────────────────────────────
    s = tracker.summary()
    _banner("📊 PRECISIÓN ACUMULADA")
    if s["total"] > 0:
        print(f"  Partidos evaluados: {s['total']}")
        print(f"  ✅ Correctos:        {s['correct']}")
        print(f"  ❌ Incorrectos:      {s['wrong']}")
        print(f"  🎯 Precisión:        {s['accuracy']}%")
    else:
        print("  Aún no hay partidos con resultado real registrados")
    print(f"  ⏳ Pendientes:       {s['pending']}")
    print()


if __name__ == "__main__":
    main()
