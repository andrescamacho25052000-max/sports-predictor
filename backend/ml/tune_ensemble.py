"""
ml/tune_ensemble.py — Afina el ensamble (XGBoost + Poisson) y la calibracion.

Idea (punto #1 y #4b del plan de mejora):
- El XGBoost y el Poisson son dos senales independientes del 1X2. Mezclarlas
  (ensamble) suele mejorar la calibracion.
- Luego se aplica calibracion por temperatura (un parametro T) para que las
  probabilidades no sean ni muy confiadas ni muy tibias.

Se busca el peso de mezcla w y la temperatura T que minimizan el RPS en un
tramo de VALIDACION temporal, y se reporta la mejora en el tramo de PRUEBA
(nunca visto). Los parametros ganadores se guardan en ml/data/ensemble_config.json
para usarse en produccion (backend/ensemble.py).

Uso:  python -m ml.tune_ensemble
"""
import json
import os

import numpy as np
import pandas as pd
from xgboost import XGBClassifier

from ml.train import FEATURES
from ml.backtest import rps
from sklearn.metrics import accuracy_score, log_loss

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CONFIG_PATH = os.path.join(DATA_DIR, "ensemble_config.json")

HOME_ADVANTAGE = 1.15
LEAGUE_SCORED, LEAGUE_CONCEDED = 1.45, 1.15
PRIOR_W = 2
MAX_GOALS = 7


def _pmf(k, lam):
    from math import exp, factorial
    return exp(-lam) * (lam ** k) / factorial(k) if lam > 0 else (1.0 if k == 0 else 0.0)


def poisson_1x2(hgf5, hga5, agf5, aga5):
    """Probabilidades [Local, Empate, Visitante] via Poisson desde goles de los ultimos 5."""
    # tasa por partido con prior bayesiano ligero (2 partidos a promedio de liga)
    h_scored = (hgf5 + LEAGUE_SCORED * PRIOR_W) / (5 + PRIOR_W)
    h_conc   = (hga5 + LEAGUE_CONCEDED * PRIOR_W) / (5 + PRIOR_W)
    a_scored = (agf5 + LEAGUE_SCORED * PRIOR_W) / (5 + PRIOR_W)
    a_conc   = (aga5 + LEAGUE_CONCEDED * PRIOR_W) / (5 + PRIOR_W)
    lam_h = (h_scored + a_conc) / 2 * HOME_ADVANTAGE
    lam_a = (a_scored + h_conc) / 2
    ph = [_pmf(k, lam_h) for k in range(MAX_GOALS + 1)]
    pa = [_pmf(k, lam_a) for k in range(MAX_GOALS + 1)]
    pH = pD = pA = 0.0
    for h in range(MAX_GOALS + 1):
        for a in range(MAX_GOALS + 1):
            p = ph[h] * pa[a]
            if h > a:   pH += p
            elif h == a: pD += p
            else:       pA += p
    s = pH + pD + pA
    return [pH / s, pD / s, pA / s]


def _poisson_matrix(df):
    return np.array([poisson_1x2(r.home_gf_5, r.home_ga_5, r.away_gf_5, r.away_ga_5)
                     for r in df.itertuples()])


def _temperature(probs, T):
    """Calibracion por temperatura: aplana (T>1) o agudiza (T<1) las probabilidades."""
    p = np.power(np.clip(probs, 1e-9, 1.0), 1.0 / T)
    return p / p.sum(axis=1, keepdims=True)


def _blend(xgb, poi, w):
    p = w * xgb + (1 - w) * poi
    return p / p.sum(axis=1, keepdims=True)


def run():
    df = pd.read_csv(os.path.join(DATA_DIR, "dataset.csv"))
    n = len(df)
    i_tr, i_va = int(n * 0.70), int(n * 0.85)
    train, val, test = df.iloc[:i_tr], df.iloc[i_tr:i_va], df.iloc[i_va:]

    model = XGBClassifier(
        n_estimators=400, max_depth=4, learning_rate=0.04,
        subsample=0.80, colsample_bytree=0.80,
        objective="multi:softprob", num_class=3, eval_metric="mlogloss", random_state=42,
    )
    model.fit(train[FEATURES].values, train["result"].values)

    xgb_va = model.predict_proba(val[FEATURES].values)
    xgb_te = model.predict_proba(test[FEATURES].values)
    poi_va, poi_te = _poisson_matrix(val), _poisson_matrix(test)
    y_va, y_te = val["result"].values, test["result"].values

    # ── Busqueda de w (mezcla) y T (temperatura) que minimizan RPS en validacion ──
    best = {"w": 1.0, "T": 1.0, "rps": 1e9}
    for w in np.arange(0.0, 1.01, 0.05):
        blended = _blend(xgb_va, poi_va, w)
        for T in np.arange(0.6, 2.41, 0.1):
            cal = _temperature(blended, T)
            r = rps(cal, y_va)
            if r < best["rps"]:
                best = {"w": round(float(w), 2), "T": round(float(T), 2), "rps": r}

    def metrics(probs, y):
        return {
            "accuracy": round(accuracy_score(y, probs.argmax(1)), 4),
            "log_loss": round(log_loss(y, probs, labels=[0, 1, 2]), 4),
            "rps":      round(rps(probs, y), 4),
        }

    # Evaluacion en TEST (nunca visto)
    ens = _blend(xgb_te, poi_te, best["w"])
    ens_cal = _temperature(ens, best["T"])
    report = {
        "split": {"train": len(train), "val": len(val), "test": len(test)},
        "best_params": {"w_xgboost": best["w"], "temperature": best["T"]},
        "test": {
            "1_xgboost_solo":        metrics(xgb_te, y_te),
            "2_poisson_solo":        metrics(poi_te, y_te),
            "3_ensamble":            metrics(ens, y_te),
            "4_ensamble_calibrado":  metrics(ens_cal, y_te),
        },
    }

    json.dump({"w_xgboost": best["w"], "temperature": best["T"]},
              open(CONFIG_PATH, "w"), indent=2)
    return report


if __name__ == "__main__":
    rep = run()
    print(json.dumps(rep, indent=2, ensure_ascii=False))
    t = rep["test"]
    print("\n== TEST (partidos nunca vistos) ==  [accuracy mayor mejor; log_loss y rps menor mejor]")
    for k, v in t.items():
        print(f"  {k:24s} acc={v['accuracy']:.3f}  logloss={v['log_loss']:.4f}  rps={v['rps']:.4f}")
    print(f"\nParametros guardados en ensemble_config.json: {rep['best_params']}")
