"""
ml/collect.py — Descarga datos históricos de football-data.org.

Guarda los resultados en ml/data/{LIGA}_{TEMPORADA}.json para no
repetir las descargas. Respeta el límite de 10 req/min con pausa
de 7 segundos entre llamadas.

Uso:
    cd backend
    python -m ml.collect
"""
import sys, os, json, time

# Asegurar que backend/ está en el path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from football_api import _get   # reutiliza clave, caché y timeouts

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# Solo ligas disponibles en el plan gratuito para historiales de equipo
LEAGUES = {
    "PL":  "Premier League",
    "PD":  "La Liga",
    "BL1": "Bundesliga",
    "SA":  "Serie A",
    "FL1": "Ligue 1",
}
# Últimas 3 temporadas completas
SEASONS = [2022, 2023, 2024]


def collect_all(force: bool = False) -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    total = 0

    for code, name in LEAGUES.items():
        for season in SEASONS:
            path = os.path.join(DATA_DIR, f"{code}_{season}.json")

            if os.path.exists(path) and not force:
                with open(path, encoding="utf-8") as f:
                    matches = json.load(f)
                n = len([m for m in matches if m.get("status") == "FINISHED"])
                print(f"  [caché] {name} {season}-{season+1}: {n} partidos")
                total += n
                continue

            print(f"  ↓ Descargando {name} temporada {season}-{season+1}…", end=" ", flush=True)
            data = _get(f"/competitions/{code}/matches?season={season}")

            if not data or "matches" not in data:
                print("sin datos")
                time.sleep(7)
                continue

            matches = data["matches"]
            with open(path, "w", encoding="utf-8") as f:
                json.dump(matches, f, ensure_ascii=False)

            finished = len([m for m in matches if m.get("status") == "FINISHED"])
            print(f"{finished} partidos guardados")
            total += finished
            time.sleep(7)   # respeta 10 req/min

    print(f"\n✓ Total: {total} partidos disponibles para entrenamiento")
    return total


if __name__ == "__main__":
    force = "--force" in sys.argv
    print("=" * 55)
    print("  PASO 1 — Descarga de datos históricos")
    print("=" * 55)
    collect_all(force=force)
