"""
ml/backtest.py — Evaluacion honesta del modelo 1X2 con metricas de apuestas.

Mide el modelo sobre un holdout TEMPORAL (los partidos mas recientes), no con
una division aleatoria, para reflejar el uso real (predecir el futuro).

Metricas:
- Accuracy: % de aciertos del resultado (1X2).
- Log-loss: penaliza probabilidades mal calibradas (menor = mejor).
- RPS (Ranked Probability Score): metrica estandar para 1X2 ordenado
  (Local < Empate < Visitante). Menor = mejor.

Uso:  python -m ml.backtest
"""
import os

import numpy as np
import pandas as pd
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, log_loss

from ml.train import FEATURES, LABELS

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
TEST_FRACTION = 0.20  # ultimo 20% (mas reciente) como prueba


def rps(probs: np.ndarray, y_true: np.ndarray) -> float:
    """Ranked Probability Score medio para 1X2 (clases ordenadas 0,1,2).

    Args:
        probs (np.ndarray): Matriz (n, 3) de probabilidades [Local, Empate, Visitante].
        y_true (np.ndarray): Vector (n,) con la clase real (0/1/2).

    Returns:
        float: RPS promedio (0 = perfecto, menor es mejor).
    """
    r = probs.shape[1]
    cum_p = np.cumsum(probs, axis=1)
    onehot = np.zeros_like(probs)
    onehot[np.arange(len(y_true)), y_true] = 1.0
    cum_o = np.cumsum(onehot, axis=1)
    return float(np.mean(np.sum((cum_p[:, :-1] - cum_o[:, :-1]) ** 2, axis=1) / (r - 1)))


def _new_model() -> XGBClassifier:
    return XGBClassifier(
        n_estimators=400, max_depth=4, learning_rate=0.04,
        subsample=0.80, colsample_bytree=0.80,
        objective="multi:softprob", num_class=3, eval_metric="mlogloss",
        random_state=42,
    )


def run() -> dict:
    """Corre el backtest temporal y devuelve las metricas."""
    df = pd.read_csv(os.path.join(DATA_DIR, "dataset.csv"))
    n = len(df)
    split = int(n * (1 - TEST_FRACTION))
    train, test = df.iloc[:split], df.iloc[split:]

    X_tr, y_tr = train[FEATURES].values, train["result"].values
    X_te, y_te = test[FEATURES].values, test["result"].values

    model = _new_model()
    model.fit(X_tr, y_tr)
    proba = model.predict_proba(X_te)
    preds = proba.argmax(axis=1)

    # ── Baselines de referencia ──────────────────────────────────────────────
    # 1) Siempre "Local"
    base_home_acc = accuracy_score(y_te, np.zeros_like(y_te))
    # 2) Tasas base del set de entrenamiento (probabilidad constante)
    rates = np.bincount(y_tr, minlength=3) / len(y_tr)
    proba_base = np.tile(rates, (len(y_te), 1))

    metrics = {
        "n_train": int(len(train)), "n_test": int(len(test)),
        "model": {
            "accuracy": round(accuracy_score(y_te, preds), 4),
            "log_loss": round(log_loss(y_te, proba, labels=[0, 1, 2]), 4),
            "rps":      round(rps(proba, y_te), 4),
        },
        "baseline_siempre_local": {"accuracy": round(base_home_acc, 4)},
        "baseline_tasas_base": {
            "log_loss": round(log_loss(y_te, proba_base, labels=[0, 1, 2]), 4),
            "rps":      round(rps(proba_base, y_te), 4),
        },
    }
    return metrics


if __name__ == "__main__":
    import json
    m = run()
    print(json.dumps(m, indent=2, ensure_ascii=False))
    print()
    print("Interpretacion:")
    print(f"  Accuracy modelo: {m['model']['accuracy']:.1%}  "
          f"(vs siempre-local {m['baseline_siempre_local']['accuracy']:.1%})")
    print(f"  Log-loss modelo: {m['model']['log_loss']}  "
          f"(vs tasas base {m['baseline_tasas_base']['log_loss']})  [menor = mejor]")
    print(f"  RPS modelo:      {m['model']['rps']}  "
          f"(vs tasas base {m['baseline_tasas_base']['rps']})  [menor = mejor]")
