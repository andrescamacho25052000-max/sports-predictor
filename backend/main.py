from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from predictor import predict
from mock_data import LEAGUES, TEAMS

app = FastAPI(title="Sports Predictor API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "ok", "message": "Sports Predictor API v1.0"}


@app.get("/leagues")
def get_leagues():
    return {"leagues": list(LEAGUES.keys())}


@app.get("/leagues/{league}/matches")
def get_matches(league: str):
    if league not in LEAGUES:
        raise HTTPException(status_code=404, detail=f"Liga '{league}' no encontrada")
    matches = LEAGUES[league]["matches"]
    return {"league": league, "matches": matches}


@app.get("/teams")
def get_teams():
    return {"teams": list(TEAMS.keys())}


@app.get("/predict/{home}/{away}")
def get_prediction(home: str, away: str):
    if home == away:
        raise HTTPException(status_code=400, detail="Los equipos deben ser diferentes")
    result = predict(home, away)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.post("/predict")
def post_prediction(body: dict):
    home = body.get("home_team")
    away = body.get("away_team")
    if not home or not away:
        raise HTTPException(status_code=400, detail="Se requieren 'home_team' y 'away_team'")
    if home == away:
        raise HTTPException(status_code=400, detail="Los equipos deben ser diferentes")
    result = predict(home, away)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
