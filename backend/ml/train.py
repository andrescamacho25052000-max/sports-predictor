"""
ml/train.py — Entrena XGBoost y guarda el modelo.

Uso:
    cd backend
    python -m ml.train
"""
import sys, os
import pandas as pd
import numpy as np
import joblib

from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import accuracy_score, classification_report

DATA_DIR   = os.path.join(os.path.dirname(__file__), "data")
MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.pkl")

FEATURES = [
    "home_wins_5",       "home_draws_5",       "home_losses_5",
    "home_gf_5",         "home_ga_5",
    "away_wins_5",       "away_draws_5",       "away_losses_5",
    "away_gf_5",         "away_ga_5",
    "home_home_wins",    "home_home_draws",    "home_home_losses",
    "away_away_wins",    "away_away_draws",    "away_away_losses",
    "h2h_home_ratio",    "h2h_draw_ratio",
    # v2: Elo + points per game
    "elo_diff",          "elo_home_expected",
    "home_pts_per_game", "away_pts_per_game",
]
LABELS = {0: "Local", 1: "Empate", 2: "Visitante"}


def train() -> XGBClassifier:
    csv = os.path.join(DATA_DIR, "dataset.csv")
    if not os.path.exists(csv):
        print("ERROR: dataset.csv no encontrado. Ejecuta primero ml.build_dataset")
        sys.exit(1)

    df = pd.read_csv(csv)
    print(f"  Filas de entrenamiento: {len(df)}")
    print(f"  Distribución real de resultados:")
    for code, label in LABELS.items():
        n = (df["result"] == code).sum()
        print(f"    {label:10s}: {n:4d}  ({n/len(df):.1%})")

    X = df[FEATURES].values
    y = df["result"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    model = XGBClassifier(
        n_estimators      = 400,
        max_depth         = 4,
        learning_rate     = 0.04,
        subsample         = 0.80,
        colsample_bytree  = 0.80,
        min_child_weight  = 5,
        gamma             = 0.1,
        eval_metric       = "mlogloss",
        random_state      = 42,
        n_jobs            = -1,
    )

    print("\n  Entrenando…")
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False,
    )

    # ── Evaluación ────────────────────────────────────────────────
    acc_test = accuracy_score(y_test, model.predict(X_test))

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(model, X, y, cv=cv, scoring="accuracy", n_jobs=-1)

    print(f"\n  Precisión en test (20%): {acc_test:.1%}")
    print(f"  Precisión CV 5-fold:     {cv_scores.mean():.1%} ± {cv_scores.std():.1%}")
    print(f"\n  Reporte por clase:")
    report = classification_report(
        y_test, model.predict(X_test),
        target_names=[LABELS[i] for i in sorted(LABELS)],
        zero_division=0,
    )
    print(report)

    # ── Importancia de features ───────────────────────────────────
    print("  Importancia de features (aprendida):")
    importances = sorted(zip(FEATURES, model.feature_importances_), key=lambda x: -x[1])
    for feat, imp in importances:
        bar = "#" * int(imp * 60)
        print(f"    {feat:<25} {bar} {imp:.3f}")

    # ── Guardar ───────────────────────────────────────────────────
    meta = {
        "model":    model,
        "features": FEATURES,
        "labels":   LABELS,
        "accuracy": round(float(acc_test), 4),
        "cv_mean":  round(float(cv_scores.mean()), 4),
    }
    joblib.dump(meta, MODEL_PATH)
    print(f"\n  OK Modelo guardado en: {MODEL_PATH}")
    return model


if __name__ == "__main__":
    print("=" * 55)
    print("  PASO 3 — Entrenamiento XGBoost")
    print("=" * 55)
    train()
