from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from predictor import predict
from mock_data import LEAGUES, TEAMS
import football_api as fapi
import api_sports as asports
import weather_api as wapi

app = FastAPI(title="Sports Predictor API", version="3.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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


@app.get("/upcoming")
def get_upcoming():
    """Próximos partidos de todas las ligas, ordenados por fecha."""
    all_matches = []
    for league in fapi.get_leagues():
        matches = fapi.get_matches(league)
        for m in matches[:3]:          # máximo 3 partidos por liga
            all_matches.append({**m, "league": league})
    all_matches.sort(key=lambda x: x.get("date") or "")
    return {"matches": all_matches[:18]}


@app.get("/teams")
def get_teams():
    return {"teams": list(TEAMS.keys())}


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

        # Embeber partidos recientes en stats para que el predictor use descanso y forma local/visitante
        home_stats["recent_matches"] = home_recent
        away_stats["recent_matches"] = away_recent

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

    result["injuries"] = {
        "home": {"team": home, "players": home_injuries},
        "away": {"team": away, "players": away_injuries},
    }

    if stadium_info:
        result["stadium"] = stadium_info

    if weather_info:
        result["weather"] = weather_info

    return result


@app.get("/predict/{home}/{away}")
def get_prediction(home: str, away: str):
    if home == away:
        raise HTTPException(status_code=400, detail="Los equipos deben ser diferentes")
    return predict(home, away)
