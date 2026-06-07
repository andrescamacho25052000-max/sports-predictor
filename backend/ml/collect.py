"""
ml/collect.py — Descarga datos históricos de football-data.org.

Maneja 429 automáticamente: lee el tiempo de espera del mensaje
y reintenta hasta 4 veces antes de rendirse.

Uso:
    cd backend
    python -m ml.collect
"""
import sys, os, json, time, re
import requests
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

API_KEY  = os.getenv("FOOTBALL_API_KEY")
BASE_URL = "https://api.football-data.org/v4"
HEADERS  = {"X-Auth-Token": API_KEY}
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

LEAGUES  = {"PL": "Premier League", "PD": "La Liga",
            "BL1": "Bundesliga", "SA": "Serie A", "FL1": "Ligue 1"}
SEASONS  = [2022, 2023, 2024]


def _fetch(path: str, max_retries: int = 4) -> dict | None:
    url = f"{BASE_URL}{path}"
    for attempt in range(max_retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)

            if r.status_code == 200:
                return r.json()

            if r.status_code == 429:
                # Extraer segundos del mensaje, ej: "Wait 37 seconds."
                msg = ""
                try:
                    msg = r.json().get("message", "")
                except Exception:
                    pass
                nums = re.findall(r"\d+", msg)
                wait = int(nums[0]) + 5 if nums else 70
                print(f"\n    ⏳ Rate limit — esperando {wait}s y reintentando "
                      f"({attempt+1}/{max_retries})…", flush=True)
                time.sleep(wait)
                continue

            print(f"\n    Error HTTP {r.status_code}")
            return None

        except Exception as e:
            print(f"\n    Excepción: {e}")
            if attempt < max_retries - 1:
                time.sleep(15)
    return None


def collect_all(force: bool = False) -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    total = 0

    for code, name in LEAGUES.items():
        for season in SEASONS:
            path = os.path.join(DATA_DIR, f"{code}_{season}.json")

            if os.path.exists(path) and not force:
                with open(path, encoding="utf-8") as f:
                    raw = json.load(f)
                n = len([m for m in raw if m.get("status") == "FINISHED"])
                print(f"  [caché] {name} {season}-{season+1}: {n} partidos")
                total += n
                continue

            print(f"  ↓  {name} {season}-{season+1}…", end=" ", flush=True)
            data = _fetch(f"/competitions/{code}/matches?season={season}")

            if not data or "matches" not in data:
                print("sin datos — continuando")
                time.sleep(8)
                continue

            raw = data["matches"]
            with open(path, "w", encoding="utf-8") as f:
                json.dump(raw, f, ensure_ascii=False)

            finished = len([m for m in raw if m.get("status") == "FINISHED"])
            print(f"{finished} partidos guardados ✓")
            total += finished

            # Pausa larga entre llamadas para no agotar las 10 req/min
            if not (code == list(LEAGUES)[-1] and season == SEASONS[-1]):
                print(f"     (pausa 12s…)", end="\r", flush=True)
                time.sleep(12)

    print(f"\n✓ Total: {total} partidos descargados")
    return total


if __name__ == "__main__":
    force = "--force" in sys.argv
    print("=" * 55)
    print("  PASO 1 — Descarga de datos históricos")
    print("=" * 55)
    collect_all(force=force)
