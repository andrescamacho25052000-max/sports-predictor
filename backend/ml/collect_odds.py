"""
ml/collect_odds.py — Descarga cuotas historicas (football-data.co.uk via espejo GitHub).

La fuente directa (football-data.co.uk) esta bloqueada por el ISP en Colombia
(Coljuegos), asi que se usa un espejo en GitHub (no bloqueado). Se extraen el
marcador y las cuotas 1X2 promedio del mercado para las 5 ligas del proyecto.

Salida: ml/data/market_odds.csv  (league, date, home, away, hg, ag, odd_h, odd_d, odd_a)

Uso:  python -m ml.collect_odds
"""
import csv
import io
import os
from datetime import datetime

import requests

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
BASE = "https://raw.githubusercontent.com/huhao930422-debug/football-odds-mirror/master/data"
UA = {"User-Agent": "Mozilla/5.0"}

# Liga (codigo interno DC) -> carpeta del espejo
LEAGUES = {
    "PL":  "premier-league",
    "PD":  "la-liga",
    "BL1": "bundesliga",
    "SA":  "serie-a",
    "FL1": "ligue-1",
}
API = "https://api.github.com/repos/huhao930422-debug/football-odds-mirror/contents/data"
# Si ALL_SEASONS, se descubren todas las temporadas por liga (para el backtest ampliado).
SEASONS = ["2324", "2425"]  # por defecto: 2 temporadas
ALL_SEASONS = os.getenv("ODDS_ALL_SEASONS", "") == "1"


def _discover_seasons(folder: str) -> list[str]:
    """Lista todas las temporadas (codigos tipo '2324') disponibles para una liga."""
    try:
        r = requests.get(f"{API}/{folder}", timeout=30, headers=UA)
        if r.status_code != 200:
            return SEASONS
        out = []
        for it in r.json():
            n = it.get("name", "")
            if n.startswith("season-") and n.endswith(".csv"):
                out.append(n[len("season-"):-len(".csv")])
        return sorted(out) or SEASONS
    except Exception:
        return SEASONS


def _to_iso(d: str) -> str | None:
    """Convierte fecha DD/MM/YYYY (o DD/MM/YY) a ISO YYYY-MM-DD."""
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(d, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def collect() -> int:
    """Descarga y consolida las cuotas. Devuelve el numero de partidos guardados."""
    rows_out = []
    for code, folder in LEAGUES.items():
        seasons = _discover_seasons(folder) if ALL_SEASONS else SEASONS
        for season in seasons:
            url = f"{BASE}/{folder}/season-{season}.csv"
            try:
                r = requests.get(url, timeout=30, headers=UA)
                if r.status_code != 200:
                    print(f"[Odds] {code} {season}: HTTP {r.status_code}")
                    continue
            except Exception as e:
                print(f"[Odds] {code} {season}: {e}")
                continue

            rows = list(csv.DictReader(io.StringIO(r.text)))
            n = 0
            for row in rows:
                date = _to_iso((row.get("Date") or "").strip())
                home = (row.get("HomeTeam") or "").strip()
                away = (row.get("AwayTeam") or "").strip()
                hg, ag = _f(row.get("FTHG")), _f(row.get("FTAG"))
                # Cuotas: promedio del mercado (AvgH/D/A); fallback a Bet365
                oh = _f(row.get("AvgH")) or _f(row.get("B365H"))
                od = _f(row.get("AvgD")) or _f(row.get("B365D"))
                oa = _f(row.get("AvgA")) or _f(row.get("B365A"))
                if not (date and home and away and hg is not None and ag is not None
                        and oh and od and oa):
                    continue
                rows_out.append({
                    "league": code, "date": date, "home": home, "away": away,
                    "hg": int(hg), "ag": int(ag),
                    "odd_h": oh, "odd_d": od, "odd_a": oa,
                })
                n += 1
            print(f"[Odds] {code} {season}: {n} partidos con cuotas")

    rows_out.sort(key=lambda x: x["date"])
    out_path = os.path.join(DATA_DIR, "market_odds.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["league", "date", "home", "away",
                                          "hg", "ag", "odd_h", "odd_d", "odd_a"])
        w.writeheader()
        w.writerows(rows_out)
    print(f"[Odds] Guardados {len(rows_out)} partidos en {out_path}")
    return len(rows_out)


if __name__ == "__main__":
    collect()
