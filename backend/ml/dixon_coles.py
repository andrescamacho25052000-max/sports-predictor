"""
ml/dixon_coles.py — Modelo Dixon-Coles (1997) con decaimiento temporal.

Estandar estadistico del futbol: estima para cada equipo una fuerza de ataque y
una de defensa, mas una ventaja de localia global (gamma) y una correccion de
marcadores bajos (rho). Se ajusta por MAXIMA VEROSIMILITUD ponderando mas los
partidos recientes (time-decay, parametro xi).

Se ajusta POR LIGA (los equipos solo son comparables dentro de su liga). A partir
de los parametros se calcula la matriz de marcadores y de ahi el 1X2.

Referencia: Dixon & Coles (1997), "Modelling Association Football Scores".

Uso (backtest):  python -m ml.dixon_coles
"""
import glob
import json
import math
import os
from datetime import datetime

import numpy as np
from scipy.optimize import minimize
from scipy.special import gammaln

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
MAX_GOALS = 10
DEFAULT_XI = 0.0018  # decaimiento por dia (~vida media de 1 año)
RHO_BOUND = 0.1


# ─── Carga de partidos crudos ─────────────────────────────────────────────────

def parse_matches() -> list[dict]:
    """Lee los JSON de football-data.org y devuelve partidos terminados.

    Returns:
        list[dict]: cada uno {league, date, home, away, hg, ag}.
    """
    LEAGUE_FILES = {"PL", "PD", "BL1", "SA", "FL1"}
    out = []
    for path in glob.glob(os.path.join(DATA_DIR, "*_20*.json")):
        # Solo los datasets de ligas de clubes (PL/PD/BL1/SA/FL1)
        base = os.path.basename(path)
        if base.split("_")[0] not in LEAGUE_FILES:
            continue
        try:
            data = json.loads(open(path, encoding="utf-8").read())
        except Exception:
            continue
        matches = data if isinstance(data, list) else data.get("matches", [])
        for m in matches:
            if m.get("status") != "FINISHED":
                continue
            ft = (m.get("score") or {}).get("fullTime") or {}
            hg, ag = ft.get("home"), ft.get("away")
            if hg is None or ag is None:
                continue
            comp = (m.get("competition") or {}).get("code", base.split("_")[0])
            out.append({
                "league": comp,
                "date":   (m.get("utcDate") or "")[:10],
                "home":   (m.get("homeTeam") or {}).get("name", ""),
                "away":   (m.get("awayTeam") or {}).get("name", ""),
                "hg":     int(hg),
                "ag":     int(ag),
            })
    out.sort(key=lambda x: x["date"])
    return out


# ─── Ajuste del modelo ────────────────────────────────────────────────────────

def _tau(hg, ag, lh, la, rho):
    """Correccion Dixon-Coles de marcadores bajos (vectorizada)."""
    t = np.ones_like(lh, dtype=float)
    m00 = (hg == 0) & (ag == 0)
    m01 = (hg == 0) & (ag == 1)
    m10 = (hg == 1) & (ag == 0)
    m11 = (hg == 1) & (ag == 1)
    t[m00] = 1.0 - lh[m00] * la[m00] * rho
    t[m01] = 1.0 + lh[m01] * rho
    t[m10] = 1.0 + la[m10] * rho
    t[m11] = 1.0 - rho
    return np.clip(t, 1e-9, None)


def fit_league(matches: list[dict], ref_date: str, xi: float = DEFAULT_XI) -> dict | None:
    """Ajusta Dixon-Coles a los partidos de UNA liga.

    Args:
        matches (list[dict]): partidos de la liga (con hg, ag, date).
        ref_date (str): fecha de referencia (YYYY-MM-DD) para el decaimiento.
        xi (float): tasa de decaimiento temporal por dia.

    Returns:
        dict | None: parametros {teams, att, dff, mu, gamma, rho} o None si pocos datos.
    """
    if len(matches) < 30:
        return None
    teams = sorted({m["home"] for m in matches} | {m["away"] for m in matches})
    idx = {t: i for i, t in enumerate(teams)}
    n = len(teams)

    home_i = np.array([idx[m["home"]] for m in matches])
    away_i = np.array([idx[m["away"]] for m in matches])
    hg = np.array([m["hg"] for m in matches])
    ag = np.array([m["ag"] for m in matches])

    ref = datetime.fromisoformat(ref_date)
    days = np.array([(ref - datetime.fromisoformat(m["date"])).days for m in matches], dtype=float)
    w = np.exp(-xi * np.clip(days, 0, None))

    lg_hg = gammaln(hg + 1)
    lg_ag = gammaln(ag + 1)

    def neg_ll(p):
        att = p[0:n]; dff = p[n:2 * n]; mu, gamma, rho = p[2 * n], p[2 * n + 1], p[2 * n + 2]
        att = att - att.mean(); dff = dff - dff.mean()
        log_lh = mu + gamma + att[home_i] + dff[away_i]
        log_la = mu + att[away_i] + dff[home_i]
        lh = np.exp(np.clip(log_lh, -3, 3)); la = np.exp(np.clip(log_la, -3, 3))
        lp_h = hg * log_lh - lh - lg_hg
        lp_a = ag * log_la - la - lg_ag
        ll = np.log(_tau(hg, ag, lh, la, rho)) + lp_h + lp_a
        return -np.sum(w * ll)

    x0 = np.zeros(2 * n + 3)
    x0[2 * n] = np.log(max(np.average(hg, weights=w), 0.5))  # mu
    x0[2 * n + 1] = 0.25   # gamma (ventaja local)
    x0[2 * n + 2] = -0.03  # rho
    bounds = [(-2, 2)] * (2 * n) + [(-1, 2), (-0.5, 0.8), (-RHO_BOUND, RHO_BOUND)]
    res = minimize(neg_ll, x0, method="L-BFGS-B", bounds=bounds,
                   options={"maxiter": 400})
    p = res.x
    att = p[0:n] - p[0:n].mean()
    dff = p[n:2 * n] - p[n:2 * n].mean()
    return {"teams": teams, "att": att.tolist(), "dff": dff.tolist(),
            "mu": float(p[2 * n]), "gamma": float(p[2 * n + 1]), "rho": float(p[2 * n + 2])}


def predict_1x2(params: dict, home: str, away: str) -> list[float] | None:
    """Probabilidades [Local, Empate, Visitante] para un enfrentamiento.

    Returns:
        list[float] | None: [pH, pD, pA] o None si algun equipo no esta en el modelo.
    """
    teams = params["teams"]
    if home not in teams or away not in teams:
        return None
    idx = {t: i for i, t in enumerate(teams)}
    att, dff = params["att"], params["dff"]
    mu, gamma, rho = params["mu"], params["gamma"], params["rho"]
    i, j = idx[home], idx[away]
    lh = np.exp(mu + gamma + att[i] + dff[j])
    la = np.exp(mu + att[j] + dff[i])

    ph = np.array([math.exp(-lh) * lh ** k / math.factorial(k) for k in range(MAX_GOALS + 1)])
    pa = np.array([math.exp(-la) * la ** k / math.factorial(k) for k in range(MAX_GOALS + 1)])
    M = np.outer(ph, pa)
    # correccion de marcadores bajos
    M[0, 0] *= 1.0 - lh * la * rho
    M[0, 1] *= 1.0 + lh * rho
    M[1, 0] *= 1.0 + la * rho
    M[1, 1] *= 1.0 - rho
    M = np.clip(M, 0, None)
    M /= M.sum()
    pH = np.tril(M, -1).sum()   # home > away
    pD = np.trace(M)            # home == away
    pA = np.triu(M, 1).sum()    # home < away
    s = pH + pD + pA
    return [pH / s, pD / s, pA / s]


# ─── Build (guardar parametros) + runtime ─────────────────────────────────────

PARAMS_PATH = os.path.join(DATA_DIR, "dixon_coles.json")

# Nombre de liga (interno de la app) -> codigo de competicion de los JSON
LEAGUE_CODES = {
    "Premier League": "PL",
    "La Liga":        "PD",
    "Bundesliga":     "BL1",
    "Serie A":        "SA",
    "Ligue 1":        "FL1",
}

_params: dict | None = None


def build(xi: float = DEFAULT_XI) -> dict:
    """Ajusta Dixon-Coles por liga con TODOS los partidos y guarda los parametros.

    Returns:
        dict: resumen {liga: n_equipos}.
    """
    matches = parse_matches()
    if not matches:
        raise RuntimeError("No hay partidos para ajustar Dixon-Coles.")
    ref = matches[-1]["date"]
    leagues = sorted({m["league"] for m in matches})
    out, summary = {}, {}
    for lg in leagues:
        lgm = [m for m in matches if m["league"] == lg]
        p = fit_league(lgm, ref_date=ref, xi=xi)
        if p:
            out[lg] = p
            summary[lg] = len(p["teams"])
    out["_meta"] = {"xi": xi, "ref_date": ref, "built_at": datetime.utcnow().isoformat()}
    open(PARAMS_PATH, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False))
    return summary


def reload_params() -> None:
    global _params
    _params = None


def _load() -> dict:
    global _params
    if _params is None:
        try:
            _params = json.loads(open(PARAMS_PATH, encoding="utf-8").read())
        except Exception:
            _params = {}
    return _params


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def _match_team(name: str, teams: list) -> str | None:
    n = _norm(name)
    if not n:
        return None
    for t in teams:
        if _norm(t) == n:
            return t
    for t in teams:
        tn = _norm(t)
        if n in tn or tn in n:
            return t
    return None


def is_ready() -> bool:
    p = _load()
    return bool(p) and any(k != "_meta" for k in p)


def predict_runtime(league_display: str, home: str, away: str) -> dict | None:
    """Prediccion 1X2 en runtime para un partido, si la liga/equipos estan cubiertos.

    Args:
        league_display (str): Nombre de la liga como lo usa la app.
        home (str): Equipo local.
        away (str): Equipo visitante.

    Returns:
        dict | None: {home_win, draw, away_win} en %, o None si no hay cobertura.
    """
    code = LEAGUE_CODES.get(league_display)
    params = _load().get(code) if code else None
    if not params:
        return None
    h = _match_team(home, params["teams"])
    a = _match_team(away, params["teams"])
    if not h or not a or h == a:
        return None
    pr = predict_1x2(params, h, a)
    if pr is None:
        return None
    return {"home_win": round(float(pr[0]) * 100, 1),
            "draw":     round(float(pr[1]) * 100, 1),
            "away_win": round(float(pr[2]) * 100, 1)}


# ─── Modelo NACIONAL (selecciones) ────────────────────────────────────────────

NATIONAL_PARAMS_PATH = os.path.join(DATA_DIR, "dixon_coles_national.json")
_national: dict | None = None


def build_national(since="2000-01-01", xi=DEFAULT_XI) -> dict:
    """Ajusta Dixon-Coles al pool de SELECCIONES y guarda los parametros.

    Usa international_results.csv (partidos internacionales desde 1872; se toma
    desde `since` por relevancia). Un solo modelo global (las selecciones se
    comparan entre si vía partidos cruzados). Guarda dixon_coles_national.json.
    """
    import csv
    rows = []
    with open(os.path.join(DATA_DIR, "international_results.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            hg, ag = r["home_score"].strip(), r["away_score"].strip()
            d = r["date"].strip()
            if not (hg.isdigit() and ag.isdigit()) or d < since:
                continue
            rows.append({"home": r["home_team"].strip(), "away": r["away_team"].strip(),
                         "hg": int(hg), "ag": int(ag), "date": d})
    if not rows:
        raise RuntimeError("No hay partidos internacionales para ajustar.")
    ref = max(r["date"] for r in rows)
    p = fit_league(rows, ref_date=ref, xi=xi)
    if not p:
        raise RuntimeError("No se pudo ajustar el modelo nacional.")
    p["_meta"] = {"since": since, "ref_date": ref, "matches": len(rows),
                  "built_at": datetime.utcnow().isoformat()}
    open(NATIONAL_PARAMS_PATH, "w", encoding="utf-8").write(json.dumps(p, ensure_ascii=False))
    return {"teams": len(p["teams"]), "matches": len(rows), "ref_date": ref}


def reload_national() -> None:
    global _national
    _national = None


def _load_national() -> dict:
    global _national
    if _national is None:
        try:
            _national = json.loads(open(NATIONAL_PARAMS_PATH, encoding="utf-8").read())
        except Exception:
            _national = {}
    return _national


def national_ready() -> bool:
    return bool(_load_national().get("teams"))


def predict_national(home: str, away: str) -> dict | None:
    """Prediccion 1X2 para un partido de selecciones (o None si no aplica).

    Devuelve None si algun equipo no esta en el modelo nacional (p.ej. si es un
    partido de clubes), asi que es seguro llamarlo siempre.
    """
    p = _load_national()
    if not p.get("teams"):
        return None
    h = _match_team(home, p["teams"])
    a = _match_team(away, p["teams"])
    if not h or not a or h == a:
        return None
    pr = predict_1x2(p, h, a)
    if pr is None:
        return None
    return {"home_win": round(float(pr[0]) * 100, 1),
            "draw":     round(float(pr[1]) * 100, 1),
            "away_win": round(float(pr[2]) * 100, 1)}


# ─── Backtest ─────────────────────────────────────────────────────────────────

def _rps(probs, y):
    cp = np.cumsum(probs, axis=1)
    oh = np.zeros_like(probs); oh[np.arange(len(y)), y] = 1
    co = np.cumsum(oh, axis=1)
    return float(np.mean(np.sum((cp[:, :-1] - co[:, :-1]) ** 2, axis=1) / 2))


def backtest(xi: float = DEFAULT_XI, test_fraction: float = 0.15) -> dict:
    """Backtest temporal: ajusta por liga en el train y evalua en el test."""
    matches = parse_matches()
    n = len(matches)
    split = int(n * (1 - test_fraction))
    cutoff = matches[split]["date"]
    train, test = matches[:split], matches[split:]

    # ajustar un modelo por liga con los partidos de entrenamiento
    leagues = sorted({m["league"] for m in train})
    params = {}
    for lg in leagues:
        lg_matches = [m for m in train if m["league"] == lg]
        p = fit_league(lg_matches, ref_date=cutoff, xi=xi)
        if p:
            params[lg] = p

    probs, ys = [], []
    for m in test:
        p = params.get(m["league"])
        if not p:
            continue
        pr = predict_1x2(p, m["home"], m["away"])
        if pr is None:
            continue
        probs.append(pr)
        ys.append(0 if m["hg"] > m["ag"] else 1 if m["hg"] == m["ag"] else 2)

    probs = np.array(probs); ys = np.array(ys)
    from sklearn.metrics import accuracy_score, log_loss
    return {
        "xi": xi, "n_train": len(train), "n_test_evaluados": int(len(ys)),
        "accuracy": round(accuracy_score(ys, probs.argmax(1)), 4),
        "log_loss": round(log_loss(ys, probs, labels=[0, 1, 2]), 4),
        "rps": round(_rps(probs, ys), 4),
    }


if __name__ == "__main__":
    for xi in (0.0, DEFAULT_XI, 0.004):
        print(json.dumps(backtest(xi=xi), ensure_ascii=False))
