"""
ml/backtest_national.py — Dixon-Coles para SELECCIONES con la base ampliada.

Prueba si tener ~49.000 partidos internacionales permite modelar bien a las
selecciones (que antes eran dificiles por falta de datos). Ajusta Dixon-Coles
sobre el pool nacional (con decaimiento temporal) y evalua en partidos
competitivos recientes (holdout temporal).

Uso:  python -m ml.backtest_national
"""
import csv
import os

import numpy as np
from sklearn.metrics import accuracy_score, log_loss

from ml import dixon_coles
from ml.backtest import rps

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
TRAIN_SINCE = "2000-01-01"     # relevancia: solo era moderna
TEST_SINCE = "2023-01-01"      # holdout: partidos recientes
COMPETITIVE_ONLY_TEST = True   # evaluar en partidos oficiales, no amistosos


def _load():
    rows = []
    with open(os.path.join(DATA_DIR, "international_results.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            hg, ag = r["home_score"].strip(), r["away_score"].strip()
            if not (hg.isdigit() and ag.isdigit()):
                continue
            rows.append({
                "date": r["date"].strip(),
                "home": r["home_team"].strip(), "away": r["away_team"].strip(),
                "hg": int(hg), "ag": int(ag),
                "tournament": r["tournament"].strip(),
            })
    rows.sort(key=lambda x: x["date"])
    return rows


def run():
    rows = [r for r in _load() if r["date"] >= TRAIN_SINCE]
    train = [r for r in rows if r["date"] < TEST_SINCE]
    test = [r for r in rows if r["date"] >= TEST_SINCE]
    if COMPETITIVE_ONLY_TEST:
        test = [r for r in test if r["tournament"] != "Friendly"]

    print(f"Entrenamiento: {len(train)} | prueba (competitivos recientes): {len(test)}")
    print("Ajustando Dixon-Coles al pool de selecciones (puede tardar)...")
    params = dixon_coles.fit_league(train, ref_date=TEST_SINCE, xi=dixon_coles.DEFAULT_XI)
    if not params:
        print("No se pudo ajustar."); return
    print(f"Selecciones modeladas: {len(params['teams'])}")

    probs, ys = [], []
    for m in test:
        pr = dixon_coles.predict_1x2(params, m["home"], m["away"])
        if pr is None:      # equipo no visto en entrenamiento
            continue
        probs.append(pr)
        ys.append(0 if m["hg"] > m["ag"] else 1 if m["hg"] == m["ag"] else 2)
    probs, ys = np.array(probs), np.array(ys)

    # baseline: tasas base del entrenamiento
    yt = np.array([0 if m["hg"] > m["ag"] else 1 if m["hg"] == m["ag"] else 2 for m in train])
    rates = np.bincount(yt, minlength=3) / len(yt)
    base = np.tile(rates, (len(ys), 1))

    print(f"\nEvaluados: {len(ys)} partidos")
    print(f"  Dixon-Coles: acc={accuracy_score(ys, probs.argmax(1)):.3f}  "
          f"logloss={log_loss(ys, probs, labels=[0,1,2]):.4f}  rps={rps(probs, ys):.4f}")
    print(f"  Baseline:    acc={accuracy_score(ys, base.argmax(1)):.3f}  "
          f"logloss={log_loss(ys, base, labels=[0,1,2]):.4f}  rps={rps(base, ys):.4f}")


if __name__ == "__main__":
    run()
