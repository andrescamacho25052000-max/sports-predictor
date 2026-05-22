from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from predictor import predict
from mock_data import LEAGUES, TEAMS
import football_api as fapi

app = FastAPI(title="Sports Predictor API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "ok", "message": "Sports Predictor API v2.0 — datos reales"}


@app.get("/leagues")
def get_leagues():
    """Lista todas las ligas disponibles (API real + mock)."""
    real = fapi.get_leagues()
    mock = [l for l in LEAGUES if l not in real]
    return {"leagues": real + mock}


@app.get("/leagues/{league}/matches")
def get_matches(league: str):
    """Partidos programados de una liga. Primero intenta API real, luego mock."""
    # Intenta con la API real
    real_matches = fapi.get_matches(league)
    if real_matches:
        return {"league": league, "matches": real_matches, "source": "live"}

    # Fallback a mock
    if league in LEAGUES:
        return {"league": league, "matches": LEAGUES[league]["matches"], "source": "mock"}

    raise HTTPException(status_code=404, detail=f"Liga '{league}' no encontrada")


@app.get("/teams")
def get_teams():
    return {"teams": list(TEAMS.keys())}


@app.post("/predict")
def post_prediction(body: dict):
    home = body.get("home_team")
    away = body.get("away_team")
    league = body.get("league", "")

    if not home or not away:
        raise HTTPException(status_code=400, detail="Se requieren 'home_team' y 'away_team'")
    if home == away:
        raise HTTPException(status_code=400, detail="Los equipos deben ser diferentes")

    # Busca IDs de los equipos en la respuesta de la API
    home_id = body.get("home_id")
    away_id = body.get("away_id")

    home_stats = None
    away_stats = None

    # Si tenemos IDs reales, obtenemos stats de la API
    if home_id and away_id:
        home_stats = fapi.get_team_stats(home, int(home_id), league)
        away_stats = fapi.get_team_stats(away, int(away_id), league)

    result = predict(home, away, home_stats, away_stats)
    return result


@app.get("/predict/{home}/{away}")
def get_prediction(home: str, away: str):
    """Predicción simple por nombre (usa mock data o stats neutras)."""
    if home == away:
        raise HTTPException(status_code=400, detail="Los equipos deben ser diferentes")
    result = predict(home, away)
    return result
