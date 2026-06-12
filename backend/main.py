from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from predictor import predict
from mock_data import LEAGUES, TEAMS
from poisson_predictor import predict_poisson
from corners_cards_predictor import predict_corners_cards
import football_api as fapi
import api_sports as asports
import weather_api as wapi
import supabase_client as sbc
import result_checker
import asyncio

app = FastAPI(title="Sports Predictor API", version="3.1.0")


async def _result_checker_loop():
    """Revisa resultados pendientes cada hora en segundo plano."""
    await asyncio.sleep(30)  # esperar 30s al arrancar antes del primer check
    while True:
        try:
            n = await asyncio.get_event_loop().run_in_executor(
                None, result_checker.check_and_update_pending
            )
            if n:
                print(f"[Scheduler] {n} resultado(s) actualizados automaticamente")
        except Exception as e:
            print(f"[Scheduler] Error en result_checker: {e}")
        await asyncio.sleep(3600)  # cada hora


def _refresh_national_data() -> dict:
    """
    Descarga el dataset de partidos internacionales (se actualiza a diario en
    GitHub), recalcula Elo + forma de las selecciones del Mundial y recarga
    los caches en memoria. Idempotente; seguro de llamar en producción donde
    ml/data/*.json no existe (está gitignorado).
    """
    from ml.build_national_elo import rebuild
    summary = rebuild(download=True)
    fapi._national_form_cache = None   # invalidar cache de forma de selecciones
    import ml_predictor
    ml_predictor.reload_elo()
    return summary


async def _national_data_loop():
    """
    Refresca Elo y forma de selecciones cada 24h.
    Al arrancar, si los archivos no existen (deploy nuevo en Railway),
    los construye de inmediato.
    """
    from pathlib import Path
    data_dir = Path(__file__).parent / "ml" / "data"
    files_ok = (data_dir / "national_form.json").exists() and \
               (data_dir / "elo_ratings.json").exists()
    if files_ok:
        await asyncio.sleep(86400)  # ya hay datos: primer refresh en 24h
    while True:
        try:
            s = await asyncio.get_event_loop().run_in_executor(
                None, _refresh_national_data
            )
            print(f"[Scheduler] Datos de selecciones refrescados: {s}")
        except Exception as e:
            print(f"[Scheduler] Error refrescando datos de selecciones: {e}")
        await asyncio.sleep(86400)  # cada 24 horas


@app.on_event("startup")
async def warm_cache():
    """Pre-calienta el caché de partidos al arrancar para que la primera
    visita sea instantánea en vez de esperar todas las llamadas a la API."""
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    priority = [
        "Mundial FIFA",
        "Premier League", "La Liga", "Bundesliga", "Serie A", "Ligue 1",
        "Champions League", "Brasileirao Serie A", "Copa Libertadores",
    ]

    def fetch_all():
        with ThreadPoolExecutor(max_workers=9) as ex:
            list(ex.map(fapi.get_matches, priority))
        print("[Cache] Partidos pre-cargados al arrancar")

    # Ejecutar en background para no bloquear el arranque
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, fetch_all)

    # Arrancar el checker automático de resultados
    asyncio.create_task(_result_checker_loop())
    print("[Scheduler] Result checker iniciado — revisa resultados cada hora")

    # Refresco diario de Elo + forma de selecciones (y build inicial si faltan)
    asyncio.create_task(_national_data_loop())
    print("[Scheduler] Refresh de datos de selecciones iniciado — cada 24h")

import os

# En producción, FRONTEND_URL viene de la variable de entorno de Railway
# Ejemplo: https://sports-predictor.vercel.app
_frontend_url = os.getenv("FRONTEND_URL", "")
_allowed_origins = ["http://localhost:3000"]
if _frontend_url:
    _allowed_origins.append(_frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",  # cualquier deploy de Vercel
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "ok", "message": "Sports Predictor API v3.0 — jugadores, estadio y clima"}


@app.get("/leagues")
def get_leagues():
    leagues = [
        {"name": name, "region": fapi.COMPETITION_REGIONS.get(name, "🌍 Internacional")}
        for name in fapi.get_leagues()
    ]
    return {"leagues": leagues}


@app.get("/leagues/{league}/matches")
def get_matches(league: str):
    real_matches = fapi.get_matches(league)
    if real_matches:
        return {"league": league, "matches": real_matches, "source": "live"}
    if league in LEAGUES:
        return {"league": league, "matches": LEAGUES[league]["matches"], "source": "mock"}
    raise HTTPException(status_code=404, detail=f"Liga '{league}' no encontrada")


@app.get("/search")
def search_matches(q: str = ""):
    """Busca partidos próximos donde juegue el equipo indicado."""
    q_clean = q.lower().strip()
    if len(q_clean) < 2:
        return {"matches": []}

    results = []
    for league in fapi.get_leagues():
        matches = fapi.get_matches(league)
        for m in matches:
            home = (m.get("home") or "").lower()
            away = (m.get("away") or "").lower()
            if q_clean in home or q_clean in away:
                results.append({**m, "league": league})

    results.sort(key=lambda x: x.get("date") or "")
    return {"matches": results[:20]}


@app.get("/upcoming")
def get_upcoming():
    """Próximos partidos. Llama a todas las fuentes EN PARALELO para máxima velocidad."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    priority = [
        "Mundial FIFA",
        "Premier League", "La Liga", "Bundesliga", "Serie A", "Ligue 1",
        "Champions League", "Brasileirao Serie A", "Copa Libertadores",
        "Eredivisie", "Primeira Liga", "Championship", "Eurocopa",
    ]

    def fetch_fapi(league: str):
        matches = fapi.get_matches(league)
        return [(m, league) for m in matches[:4]]

    def fetch_betplay():
        matches = asports.get_betplay_fixtures(next_n=8)
        return [(m, "Liga BetPlay") for m in matches]

    all_matches = []

    with ThreadPoolExecutor(max_workers=14) as executor:
        futures = {executor.submit(fetch_fapi, league): league for league in priority}
        futures[executor.submit(fetch_betplay)] = "Liga BetPlay"

        for future in as_completed(futures):
            try:
                all_matches.extend(future.result())
            except Exception:
                pass

    all_matches.sort(key=lambda x: x[0].get("date") or "")
    result = [{**m, "league": league} for m, league in all_matches]

    # Incluir estado de cuota de API-Sports para que el frontend pueda avisar al usuario
    quota = asports.quota_status()
    return {
        "matches": result[:32],
        "betplay_quota": {
            "exhausted":  quota["exhausted"],
            "remaining":  quota["remaining"],
        },
    }


@app.get("/teams")
def get_teams():
    return {"teams": list(TEAMS.keys())}


@app.get("/teams/search")
def search_teams(q: str = ""):
    """
    Busca equipos por nombre en el índice local (sin llamadas a API externa).
    Devuelve [{"id": int, "name": str}, ...].
    Usado por el frontend para resolver team_id cuando el usuario escribe manualmente.
    """
    if len(q.strip()) < 2:
        return {"teams": []}
    results = fapi.search_teams(q.strip())
    return {"teams": results}


@app.post("/predict")
def post_prediction(body: dict):
    home   = body.get("home_team")
    away   = body.get("away_team")
    league = body.get("league", "")
    match_date = (body.get("match_date") or "")[:10]

    if not home or not away:
        raise HTTPException(status_code=400, detail="Se requieren 'home_team' y 'away_team'")
    if home == away:
        raise HTTPException(status_code=400, detail="Los equipos deben ser diferentes")

    home_id = body.get("home_id")
    away_id = body.get("away_id")

    home_stats = None
    away_stats = None
    team_data  = None

    # ── Football-Data.org: forma reciente + rankings + H2H ───────────────
    h2h_data = None
    if home_id and away_id:
        home_stats = fapi.get_team_stats(home, int(home_id), league)
        away_stats = fapi.get_team_stats(away, int(away_id), league)
        standings  = fapi.get_standings(league)

        def find_ranking(name: str) -> int:
            r = standings.get(name)
            if not r:
                for n, p in standings.items():
                    if name.lower() in n.lower() or n.lower() in name.lower():
                        return p
            return r or 99

        home_recent = fapi.get_team_recent_matches(int(home_id))
        away_recent = fapi.get_team_recent_matches(int(away_id))

        # Embeber partidos recientes y team_id en stats
        # (team_id lo usa ml_predictor para buscar el Elo en tiempo real)
        home_stats["recent_matches"] = home_recent
        away_stats["recent_matches"] = away_recent
        home_stats["team_id"] = int(home_id)
        away_stats["team_id"] = int(away_id)

        # Historial directo real
        h2h_data = fapi.get_h2h(int(home_id), int(away_id))

        team_data = {
            "home": {"ranking": find_ranking(home), "league": league, "recent_matches": home_recent},
            "away": {"ranking": find_ranking(away), "league": league, "recent_matches": away_recent},
        }

    # ── API-Sports: lesionados + estadio ─────────────────────────────────
    home_injuries = []
    away_injuries = []
    stadium_info  = None

    home_team_info = asports.search_team(home)
    away_team_info = asports.search_team(away)

    if home_team_info:
        home_injuries = asports.get_injuries(home_team_info["id"])
        stadium_info  = home_team_info["venue"]
        stadium_info["home_team_logo"] = home_team_info.get("logo", "")

    if away_team_info:
        away_injuries = asports.get_injuries(away_team_info["id"])

    # Actualizar stats con lesiones reales
    if home_stats:
        home_stats["injured_players"] = len(home_injuries)
    if away_stats:
        away_stats["injured_players"] = len(away_injuries)

    # ── Open-Meteo: clima en el estadio ──────────────────────────────────
    weather_info = None
    if stadium_info and stadium_info.get("city") and match_date:
        weather_info = wapi.get_weather(stadium_info["city"], match_date)

    # ── Predicción ───────────────────────────────────────────────────────
    result = predict(
        home, away,
        home_stats, away_stats,
        weather_info, stadium_info,
        h2h_data=h2h_data,
        match_date=match_date,
    )

    if team_data:
        result["team_stats"] = team_data

    # ── Mercados Poisson (siempre se calculan) ───────────────────────────────
    poisson_home = home_stats or {"goals_scored_last5": 7, "goals_conceded_last5": 6}
    poisson_away = away_stats or {"goals_scored_last5": 6, "goals_conceded_last5": 7}
    result["poisson"] = predict_poisson(poisson_home, poisson_away)

    # ── Córners y tarjetas (StatsBomb) ───────────────────────────────────────
    result["corners_cards"] = predict_corners_cards(home, away)

    result["injuries"] = {
        "home": {"team": home, "players": home_injuries},
        "away": {"team": away, "players": away_injuries},
    }

    if stadium_info:
        result["stadium"] = stadium_info

    if weather_info:
        result["weather"] = weather_info

    # ── Guardar predicción en Supabase ───────────────────────────────────────
    try:
        probs = result.get("probabilities", {})
        ph = probs.get("home_win", 0)
        pd = probs.get("draw", 0)
        pa = probs.get("away_win", 0)

        # Determinar ganador predicho
        best_prob = max(ph, pd, pa)
        if best_prob == ph:
            pred_winner = "Local"
            confidence  = ph
        elif best_prob == pd:
            pred_winner = "Empate"
            confidence  = pd
        else:
            pred_winner = "Visitante"
            confidence  = pa

        # Capturar features del modelo para reentrenamiento futuro
        features_snapshot = None
        if home_stats and away_stats:
            features_snapshot = {
                "home_wins_last5":    home_stats.get("wins_last5", 0),
                "home_draws_last5":   home_stats.get("draws_last5", 0),
                "home_losses_last5":  home_stats.get("losses_last5", 0),
                "home_goals_scored":  home_stats.get("goals_scored_last5", 0),
                "home_goals_conceded":home_stats.get("goals_conceded_last5", 0),
                "home_possession":    home_stats.get("possession_avg", 50),
                "home_shots":         home_stats.get("shots_on_target_avg", 0),
                "home_injured":       home_stats.get("injured_players", 0),
                "away_wins_last5":    away_stats.get("wins_last5", 0),
                "away_draws_last5":   away_stats.get("draws_last5", 0),
                "away_losses_last5":  away_stats.get("losses_last5", 0),
                "away_goals_scored":  away_stats.get("goals_scored_last5", 0),
                "away_goals_conceded":away_stats.get("goals_conceded_last5", 0),
                "away_possession":    away_stats.get("possession_avg", 50),
                "away_shots":         away_stats.get("shots_on_target_avg", 0),
                "away_injured":       away_stats.get("injured_players", 0),
                "h2h_home_wins":      h2h_data.get("wins",   0) if h2h_data else 0,
                "h2h_draws":          h2h_data.get("draws",  0) if h2h_data else 0,
                "h2h_away_wins":      h2h_data.get("losses", 0) if h2h_data else 0,
                "home_elo":           home_stats.get("elo", 1500),
                "away_elo":           away_stats.get("elo", 1500),
            }

        pred_record = {
            "home_team":      home,
            "away_team":      away,
            "league":         league or None,
            "match_date":     match_date or None,
            "home_crest":     body.get("home_crest") or None,
            "away_crest":     body.get("away_crest") or None,
            "prob_home_win":  ph,
            "prob_draw":      pd,
            "prob_away_win":  pa,
            "pred_winner":    pred_winner,
            "confidence":     confidence,
            "model_used":     result.get("model", "hybrid"),
            "xg_home":        result.get("poisson", {}).get("xg_home"),
            "xg_away":        result.get("poisson", {}).get("xg_away"),
            # IDs para búsqueda automática de resultados
            "fd_home_id":     int(home_id) if home_id else None,
            "fd_away_id":     int(away_id) if away_id else None,
            # Features para reentrenamiento incremental
            "features_json":  features_snapshot,
            "model_version":  result.get("model", "rule-based"),
        }
        saved = sbc.save_prediction(pred_record)
        if saved:
            result["prediction_id"] = saved["id"]
    except Exception as e:
        print(f"[Supabase] No se pudo guardar prediccion: {e}")

    return result


@app.get("/predictions")
def list_predictions(limit: int = 50, offset: int = 0):
    """Historial de todas las predicciones guardadas en Supabase."""
    rows = sbc.get_predictions(limit=limit, offset=offset)
    return {"predictions": rows, "count": len(rows)}


@app.get("/predictions/stats")
def prediction_stats():
    """Estadísticas globales de precisión del modelo."""
    return sbc.get_stats()


@app.post("/predictions/check-results")
async def trigger_result_check():
    """Fuerza una búsqueda inmediata de resultados pendientes (sin esperar la hora)."""
    n = await asyncio.get_event_loop().run_in_executor(
        None, result_checker.check_and_update_pending
    )
    return {"updated": n, "message": f"{n} resultado(s) actualizados"}


@app.post("/predictions/retrain")
async def trigger_retrain(body: dict = {}):
    """
    Dispara reentrenamiento incremental manual del modelo.
    También refresca el Elo y la forma de selecciones con el dataset
    internacional más reciente.
    """
    force = body.get("force", False)

    try:
        national = await asyncio.get_event_loop().run_in_executor(
            None, _refresh_national_data
        )
    except Exception as e:
        national = {"error": str(e)}

    def _retrain():
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ml"))
        from ml.incremental_trainer import run_incremental_training
        return run_incremental_training(force=force)
    result = await asyncio.get_event_loop().run_in_executor(None, _retrain)

    if isinstance(result, dict):
        result["national_data"] = national
        return result
    return {"retrain": result, "national_data": national}


@app.get("/predictions/model-evolution")
def model_evolution():
    """Historial de evolución del modelo (accuracy por cada reentrenamiento)."""
    from pathlib import Path
    import json
    meta_path = Path(__file__).parent / "ml" / "data" / "incremental_meta.json"
    if not meta_path.exists():
        return {"history": [], "total_trained": 0, "current_version": "0.0"}
    meta = json.loads(meta_path.read_text())
    return {
        "current_version": meta.get("model_version", "0.0"),
        "total_trained":   meta.get("total_trained", 0),
        "last_run":        meta.get("last_run"),
        "history":         meta.get("accuracy_history", []),
    }


@app.patch("/predictions/{prediction_id}/result")
def update_prediction_result(prediction_id: int, body: dict):
    """
    Registra el resultado real de un partido.
    Body: { "home_goals": 2, "away_goals": 1 }
    """
    home_goals = body.get("home_goals")
    away_goals = body.get("away_goals")
    if home_goals is None or away_goals is None:
        raise HTTPException(status_code=400, detail="Se requieren 'home_goals' y 'away_goals'")
    result = sbc.update_result(prediction_id, int(home_goals), int(away_goals))
    if not result:
        raise HTTPException(status_code=404, detail=f"Prediccion {prediction_id} no encontrada o error al actualizar")
    return result


@app.get("/predict/{home}/{away}")
def get_prediction(home: str, away: str):
    if home == away:
        raise HTTPException(status_code=400, detail="Los equipos deben ser diferentes")
    return predict(home, away)
