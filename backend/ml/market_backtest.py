"""
ml/market_backtest.py — Benchmark vs el mercado + backtest de valor (ROI).

Responde dos preguntas clave para un producto de apuestas por valor:
1. ¿Qué tan bueno es el modelo comparado con el mercado (el "patrón oro")?
   -> compara el RPS/log-loss de Dixon-Coles contra las cuotas del mercado.
2. ¿La estrategia de valor ganaría dinero?
   -> simula apostar 1 unidad cada vez que EV = prob_modelo x cuota - 1 supera
      un umbral, y mide el ROI sobre partidos NUNCA vistos.

Importante: el modelo NO usa las cuotas como entrada (se mantiene independiente),
para poder detectar cuando el mercado se equivoca.

Uso:  python -m ml.market_backtest
"""
import csv
import os

import numpy as np
from sklearn.metrics import accuracy_score, log_loss

from ml import dixon_coles
from ml.backtest import rps

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
TEST_FRACTION = 0.20


def _load():
    path = os.path.join(DATA_DIR, "market_odds.csv")
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    for r in rows:
        r["hg"] = int(r["hg"]); r["ag"] = int(r["ag"])
        r["odd_h"] = float(r["odd_h"]); r["odd_d"] = float(r["odd_d"]); r["odd_a"] = float(r["odd_a"])
    rows.sort(key=lambda x: x["date"])
    return rows


def _implied(oh, od, oa):
    """Probabilidades implicitas del mercado sin margen (de-vig)."""
    raw = np.array([1 / oh, 1 / od, 1 / oa])
    return raw / raw.sum()


def run():
    rows = _load()
    n = len(rows)
    split = int(n * (1 - TEST_FRACTION))
    cutoff = rows[split]["date"]
    train, test = rows[:split], rows[split:]

    # Ajustar Dixon-Coles por liga con los partidos de entrenamiento
    params = {}
    for lg in sorted({r["league"] for r in train}):
        lgm = [r for r in train if r["league"] == lg]
        p = dixon_coles.fit_league(lgm, ref_date=cutoff, xi=dixon_coles.DEFAULT_XI)
        if p:
            params[lg] = p

    model_probs, market_probs, ys, odds = [], [], [], []
    for r in test:
        p = params.get(r["league"])
        if not p:
            continue
        pr = dixon_coles.predict_1x2(p, r["home"], r["away"])
        if pr is None:
            continue
        model_probs.append(pr)
        market_probs.append(_implied(r["odd_h"], r["odd_d"], r["odd_a"]))
        odds.append([r["odd_h"], r["odd_d"], r["odd_a"]])
        ys.append(0 if r["hg"] > r["ag"] else 1 if r["hg"] == r["ag"] else 2)

    model_probs = np.array(model_probs)
    market_probs = np.array(market_probs)
    odds = np.array(odds)
    ys = np.array(ys)

    def m(probs):
        return {
            "accuracy": round(accuracy_score(ys, probs.argmax(1)), 4),
            "log_loss": round(log_loss(ys, probs, labels=[0, 1, 2]), 4),
            "rps":      round(rps(probs, ys), 4),
        }

    # ── Backtest de valor: apostar donde EV = prob x cuota - 1 > umbral ────────
    value = {}
    for thr in (0.0, 0.05, 0.10):
        bets = profit = wins = 0
        odds_taken = []
        for i in range(len(ys)):
            for o in range(3):  # 0=Local,1=Empate,2=Visitante
                ev = model_probs[i][o] * odds[i][o] - 1
                if ev > thr:
                    bets += 1
                    odds_taken.append(odds[i][o])
                    if ys[i] == o:
                        profit += odds[i][o] - 1
                        wins += 1
                    else:
                        profit -= 1
        value[f"umbral_ev_{thr:.2f}"] = {
            "apuestas": bets,
            "aciertos": wins,
            "hit_rate": round(wins / bets, 4) if bets else None,
            "roi":      round(profit / bets, 4) if bets else None,
            "cuota_media": round(float(np.mean(odds_taken)), 2) if odds_taken else None,
        }

    return {
        "n_train": len(train), "n_test": int(len(ys)),
        "modelo_dixon_coles": m(model_probs),
        "mercado": m(market_probs),
        "valor": value,
    }


if __name__ == "__main__":
    import json
    rep = run()
    print(json.dumps(rep, indent=2, ensure_ascii=False))
    print("\n== Modelo vs Mercado (RPS/log-loss menor = mejor) ==")
    print(f"  Dixon-Coles: rps={rep['modelo_dixon_coles']['rps']}  logloss={rep['modelo_dixon_coles']['log_loss']}  acc={rep['modelo_dixon_coles']['accuracy']}")
    print(f"  Mercado:     rps={rep['mercado']['rps']}  logloss={rep['mercado']['log_loss']}  acc={rep['mercado']['accuracy']}")
    print("\n== Estrategia de valor (ROI por unidad apostada) ==")
    for k, v in rep["valor"].items():
        print(f"  {k}: {v['apuestas']} apuestas, hit {v['hit_rate']}, ROI {v['roi']}, cuota media {v['cuota_media']}")
