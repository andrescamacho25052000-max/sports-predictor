"""
collect_betplay_stats.py
=========================
Descarga estadísticas de partidos de la Liga BetPlay desde API-Sports.
Diseñado para ejecutarse en múltiples días respetando el límite de 100 req/día.

Guarda progreso en: ml/data/betplay_stats_progress.json
Resultado final en: ml/data/betplay_matches.csv

Uso:
  python ml/collect_betplay_stats.py           # descarga hasta agotar quota
  python ml/collect_betplay_stats.py --status  # solo muestra progreso

El script recuerda dónde quedó y continúa al día siguiente.
"""

import os, sys, json, csv, time, requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

API_KEY   = os.getenv("API_SPORTS_KEY", "")
BASE      = "https://v3.football.api-sports.io"
HEADERS   = {"x-apisports-key": API_KEY}

DATA_DIR      = Path(__file__).parent / "data"
PROGRESS_FILE = DATA_DIR / "betplay_stats_progress.json"
OUT_CSV       = DATA_DIR / "betplay_matches.csv"
DATA_DIR.mkdir(exist_ok=True)

# Ligas BetPlay disponibles en plan gratuito (2022-2024)
SEASONS    = [2024, 2023, 2022]
LEAGUE_ID  = 239
MAX_REQUESTS_PER_RUN = 60   # conservador: 60 stats + ~3 de lista = 63/100 diarios


def get(path: str) -> dict | None:
    try:
        r = requests.get(f"{BASE}{path}", headers=HEADERS, timeout=12)
        remaining = r.headers.get("x-ratelimit-requests-remaining")
        quota_left = int(remaining) if remaining else None
        if r.status_code == 200:
            data = r.json()
            if data.get("errors"):
                print(f"  API error: {data['errors']}")
                return None
            return {"data": data, "remaining": quota_left}
        print(f"  HTTP {r.status_code}")
        return None
    except Exception as e:
        print(f"  Excepción: {e}")
        return None


def load_progress() -> dict:
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {
        "fixtures": {},       # fixture_id -> status ("ok" | "no_stats" | "error")
        "fixture_list": [],   # lista de todos los fixture_ids a procesar
        "list_fetched": False,
        "completed": False,
    }


def save_progress(prog: dict):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(prog, f, indent=2)


def save_csv(rows: list[dict]):
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    mode = "w" if not OUT_CSV.exists() else "w"
    with open(OUT_CSV, mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def extract_stats(fixture_response: dict) -> dict | None:
    """Extrae stats relevantes de la respuesta de /fixtures/statistics."""
    response = fixture_response.get("response", [])
    if len(response) < 2:
        return None

    result = {}
    for i, team_data in enumerate(response[:2]):
        prefix = "home" if i == 0 else "away"
        team_name = team_data["team"]["name"]
        result[f"{prefix}_team"] = team_name
        stats_map = {s["type"]: s["value"] for s in team_data.get("statistics", [])}

        def val(key, default=0):
            v = stats_map.get(key, default)
            if v is None:
                return default
            if isinstance(v, str) and "%" in v:
                return float(v.replace("%", ""))
            return v

        result[f"{prefix}_corners"]    = val("Corner Kicks")
        result[f"{prefix}_yellow"]     = val("Yellow Cards")
        result[f"{prefix}_red"]        = val("Red Cards")
        result[f"{prefix}_fouls"]      = val("Fouls")
        result[f"{prefix}_shots"]      = val("Total Shots")
        result[f"{prefix}_shots_ot"]   = val("Shots on Goal")
        result[f"{prefix}_possession"] = val("Ball Possession")
        result[f"{prefix}_passes"]     = val("Total passes")
        result[f"{prefix}_saves"]      = val("Goalkeeper Saves")

    return result


def main():
    if not API_KEY:
        print("ERROR: API_SPORTS_KEY no configurada en .env")
        return

    # Modo --status
    if "--status" in sys.argv:
        prog = load_progress()
        total = len(prog["fixture_list"])
        done  = sum(1 for s in prog["fixtures"].values() if s in ("ok", "no_stats"))
        ok    = sum(1 for s in prog["fixtures"].values() if s == "ok")
        print(f"Progreso BetPlay Stats:")
        print(f"  Fixtures totales: {total}")
        print(f"  Procesados:       {done} ({done/total*100:.1f}% si total>0)")
        print(f"  Con estadisticas: {ok}")
        print(f"  Pendientes:       {total - done}")
        print(f"  Completado:       {prog['completed']}")
        if OUT_CSV.exists():
            with open(OUT_CSV, encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            print(f"  CSV guardado:     {len(rows)} partidos con stats")
        return

    prog     = load_progress()
    requests_used = 0

    # ── Paso 1: obtener lista de todos los fixtures ──────────────────────────
    if not prog["list_fetched"]:
        print("Obteniendo lista de partidos BetPlay...")
        all_fixtures = []
        for season in SEASONS:
            if requests_used >= MAX_REQUESTS_PER_RUN:
                break
            res = get(f"/fixtures?league={LEAGUE_ID}&season={season}&from=2022-01-01&to=2024-12-31")
            requests_used += 1
            if not res:
                continue
            fixtures = res["data"].get("response", [])
            remaining = res["remaining"]
            finished = [f for f in fixtures if f["fixture"]["status"]["short"] == "FT"]
            for f in finished:
                all_fixtures.append({
                    "id":       f["fixture"]["id"],
                    "season":   season,
                    "date":     f["fixture"]["date"][:10],
                    "home":     f["teams"]["home"]["name"],
                    "away":     f["teams"]["away"]["name"],
                    "home_id":  f["teams"]["home"]["id"],
                    "away_id":  f["teams"]["away"]["id"],
                    "home_goals": f["goals"]["home"],
                    "away_goals": f["goals"]["away"],
                })
            print(f"  BetPlay {season}: {len(finished)} partidos terminados (quota: {remaining})")
            time.sleep(1)

        prog["fixture_list"] = all_fixtures
        prog["list_fetched"] = True
        save_progress(prog)
        print(f"Total fixtures a procesar: {len(all_fixtures)}")
    else:
        all_fixtures = prog["fixture_list"]

    # ── Paso 2: descargar estadísticas de cada fixture pendiente ────────────
    pending = [f for f in all_fixtures if str(f["id"]) not in prog["fixtures"]]
    print(f"\nPendientes: {len(pending)} | Requests disponibles hoy: ~{MAX_REQUESTS_PER_RUN - requests_used}")

    rows_ok = []
    # Cargar CSV existente
    if OUT_CSV.exists():
        with open(OUT_CSV, encoding="utf-8") as f:
            rows_ok = list(csv.DictReader(f))

    for fixture in pending:
        if requests_used >= MAX_REQUESTS_PER_RUN:
            print(f"\nLímite diario alcanzado. Vuelve mañana para continuar.")
            break

        fid  = fixture["id"]
        home = fixture["home"]
        away = fixture["away"]

        res = get(f"/fixtures/statistics?fixture={fid}")
        requests_used += 1

        if not res:
            prog["fixtures"][str(fid)] = "error"
            save_progress(prog)
            time.sleep(7)
            continue

        stats = extract_stats(res["data"])
        remaining = res["remaining"]

        if stats:
            row = {
                "fixture_id":   fid,
                "season":       fixture["season"],
                "date":         fixture["date"],
                "competition":  "Liga BetPlay",
                "home_team":    home,
                "away_team":    away,
                "home_id":      fixture["home_id"],
                "away_id":      fixture["away_id"],
                "home_goals":   fixture["home_goals"],
                "away_goals":   fixture["away_goals"],
                **stats,
            }
            rows_ok.append(row)
            prog["fixtures"][str(fid)] = "ok"
            print(f"  OK [{requests_used}] {home} vs {away} | corners {stats['home_corners']}-{stats['away_corners']} | amarillas {stats['home_yellow']}-{stats['away_yellow']} | quota: {remaining}")
        else:
            prog["fixtures"][str(fid)] = "no_stats"
            print(f"  - [{requests_used}] {home} vs {away} | sin estadísticas")

        save_progress(prog)
        time.sleep(7)  # max 10 req/min — 7s da margen seguro

    # Guardar CSV con todo lo recopilado
    save_csv(rows_ok)

    done  = sum(1 for s in prog["fixtures"].values() if s in ("ok", "no_stats"))
    total = len(all_fixtures)
    ok    = sum(1 for s in prog["fixtures"].values() if s == "ok")

    if done >= total:
        prog["completed"] = True
        save_progress(prog)
        print(f"\n✅ ¡Descarga completa! {ok} partidos con estadísticas guardados en {OUT_CSV}")
    else:
        print(f"\nProgreso: {done}/{total} ({done/total*100:.1f}%)")
        print(f"Con estadísticas: {ok} partidos")
        print(f"CSV guardado: {OUT_CSV}")
        print(f"\nVuelve mañana y ejecuta este script de nuevo para continuar.")


if __name__ == "__main__":
    main()
