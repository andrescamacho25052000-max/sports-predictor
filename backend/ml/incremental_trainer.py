"""
incremental_trainer.py
======================
Reentrenamiento incremental del modelo usando resultados reales de Supabase.

Flujo:
  1. Lee predicciones evaluadas (con resultado real) que no se han usado aún.
  2. Convierte cada predicción en un vector de features (X) y etiqueta (y).
  3. Si ya existe un modelo guardado → continúa entrenando desde donde quedó.
     Si no existe → entrena desde cero con todos los datos disponibles.
  4. Guarda el modelo actualizado y marca las filas como retrain_used=True.
  5. Guarda métricas de mejora (accuracy antes vs después).

Resultado: el modelo mejora automáticamente con cada partido real.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json
import numpy as np
from pathlib import Path
from datetime import datetime

# ── Rutas ─────────────────────────────────────────────────────────────────────
DATA_DIR    = Path(__file__).parent / "data"
MODEL_PATH  = DATA_DIR / "xgb_model.json"
META_PATH   = DATA_DIR / "incremental_meta.json"
MIN_SAMPLES = 5   # mínimo de nuevos resultados para disparar reentrenamiento

# ── Mapeo de resultado a clase ────────────────────────────────────────────────
LABEL_MAP = {"Local": 0, "Empate": 1, "Visitante": 2}
LABEL_INV = {0: "Local", 1: "Empate", 2: "Visitante"}


def _features_from_record(rec: dict) -> list[float] | None:
    """
    Convierte un registro de Supabase en vector de features.
    Usa features_json si está disponible; si no, reconstruye desde probabilidades.
    """
    features_json = rec.get("features_json")

    if features_json:
        # Features completos guardados en el momento de predecir
        f = features_json if isinstance(features_json, dict) else json.loads(features_json)
        # Vector ordenado (debe coincidir con el orden en ml_predictor.py)
        keys = [
            "home_wins_last5", "home_draws_last5", "home_losses_last5",
            "home_goals_scored", "home_goals_conceded",
            "home_possession", "home_shots", "home_injured",
            "away_wins_last5", "away_draws_last5", "away_losses_last5",
            "away_goals_scored", "away_goals_conceded",
            "away_possession", "away_shots", "away_injured",
            "h2h_home_wins", "h2h_draws", "h2h_away_wins",
            "home_elo", "away_elo",
        ]
        try:
            return [float(f.get(k, 0)) for k in keys]
        except Exception:
            pass

    # Fallback: reconstruir features aproximados desde probabilidades
    # (menos preciso, pero permite aprovechar predicciones antiguas)
    ph = float(rec.get("prob_home_win") or 33.3)
    pd = float(rec.get("prob_draw")     or 33.3)
    pa = float(rec.get("prob_away_win") or 33.3)

    # Meta-features: las probabilidades del modelo anterior como input
    # Esto es "stacking" — enseñar al nuevo modelo a corregir al viejo
    return [
        ph / 100, pd / 100, pa / 100,
        ph - pd, ph - pa, pd - pa,
        1.0 if ph > pd and ph > pa else 0.0,  # modelo predijo local
        1.0 if pd > ph and pd > pa else 0.0,  # modelo predijo empate
        1.0 if pa > ph and pa > pd else 0.0,  # modelo predijo visitante
    ]


def _load_meta() -> dict:
    if META_PATH.exists():
        return json.loads(META_PATH.read_text())
    return {
        "total_trained": 0,
        "last_run":      None,
        "accuracy_history": [],
        "model_version": "0.0",
    }


def _save_meta(meta: dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    META_PATH.write_text(json.dumps(meta, indent=2, default=str))


def run_incremental_training(force: bool = False) -> dict:
    """
    Punto de entrada principal.
    Retorna un dict con el resultado del entrenamiento.
    """
    import supabase_client as sbc

    sb = sbc.get_client()
    if not sb:
        return {"status": "error", "message": "Supabase no disponible"}

    # ── 1. Leer nuevos resultados ──────────────────────────────────────────
    query = (sb.table("predictions")
               .select("*")
               .not_.is_("result_actual", "null")
               .eq("retrain_used", False))

    if not force:
        query = query.eq("retrain_used", False)

    rows = query.execute().data or []

    if len(rows) < MIN_SAMPLES and not force:
        return {
            "status":  "skipped",
            "message": f"Solo {len(rows)} nuevos resultados (mínimo {MIN_SAMPLES}). Se reentrenará cuando haya más.",
            "new_results": len(rows),
        }

    print(f"[IncrementalTrainer] {len(rows)} nuevos resultados disponibles para entrenar")

    # ── 2. Convertir a matrices X, y ──────────────────────────────────────
    X, y = [], []
    used_ids = []

    for rec in rows:
        label = LABEL_MAP.get(rec.get("result_actual"))
        if label is None:
            continue
        feats = _features_from_record(rec)
        if feats is None:
            continue
        X.append(feats)
        y.append(label)
        used_ids.append(rec["id"])

    if len(X) < MIN_SAMPLES:
        return {
            "status":  "skipped",
            "message": f"Solo {len(X)} filas con features válidos.",
            "new_results": len(X),
        }

    X_arr = np.array(X, dtype=np.float32)
    y_arr = np.array(y, dtype=np.int32)

    # ── 3. Entrenar / actualizar modelo ───────────────────────────────────
    try:
        import xgboost as xgb
    except ImportError:
        return {"status": "error", "message": "xgboost no instalado"}

    meta    = _load_meta()
    dtrain  = xgb.DMatrix(X_arr, label=y_arr)
    params  = {
        "objective":        "multi:softprob",
        "num_class":        3,
        "max_depth":        4,
        "learning_rate":    0.05,   # tasa baja → aprendizaje suave, no olvida lo anterior
        "subsample":        0.8,
        "colsample_bytree": 0.8,
        "eval_metric":      "mlogloss",
        "verbosity":        0,
    }

    # Accuracy ANTES
    acc_before = None
    model = None
    if MODEL_PATH.exists():
        model = xgb.Booster()
        model.load_model(str(MODEL_PATH))
        preds_before = model.predict(dtrain)
        pred_labels  = np.argmax(preds_before, axis=1)
        acc_before   = float(np.mean(pred_labels == y_arr))
        print(f"[IncrementalTrainer] Accuracy ANTES: {acc_before:.1%}")

        # Continuar entrenamiento desde el modelo existente
        model = xgb.train(
            params, dtrain,
            num_boost_round = max(10, len(X) // 2),
            xgb_model       = model,
            verbose_eval    = False,
        )
    else:
        # Primera vez: entrenar desde cero
        model = xgb.train(
            params, dtrain,
            num_boost_round = max(30, len(X)),
            verbose_eval    = False,
        )

    # Accuracy DESPUÉS
    preds_after = model.predict(dtrain)
    pred_labels = np.argmax(preds_after, axis=1)
    acc_after   = float(np.mean(pred_labels == y_arr))
    print(f"[IncrementalTrainer] Accuracy DESPUÉS: {acc_after:.1%}")

    # ── 4. Guardar modelo ─────────────────────────────────────────────────
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    model.save_model(str(MODEL_PATH))

    # Nueva versión
    version_parts = meta.get("model_version", "0.0").split(".")
    new_version   = f"{version_parts[0]}.{int(version_parts[-1]) + 1}"

    # Actualizar meta
    meta["total_trained"]   += len(X)
    meta["last_run"]         = datetime.utcnow().isoformat()
    meta["model_version"]    = new_version
    meta["accuracy_history"].append({
        "date":         datetime.utcnow().isoformat(),
        "samples":      len(X),
        "acc_before":   round(acc_before, 4) if acc_before is not None else None,
        "acc_after":    round(acc_after,  4),
        "improvement":  round(acc_after - acc_before, 4) if acc_before is not None else None,
        "version":      new_version,
    })
    # Guardar solo los últimos 50 entrenamientos en el historial
    meta["accuracy_history"] = meta["accuracy_history"][-50:]
    _save_meta(meta)

    # ── 5. Marcar filas como usadas en Supabase ───────────────────────────
    if used_ids:
        try:
            sb.table("predictions").update({
                "retrain_used":   True,
                "model_version":  new_version,
            }).in_("id", used_ids).execute()
        except Exception as e:
            print(f"[IncrementalTrainer] Error marcando filas: {e}")

    improvement = (acc_after - acc_before) if acc_before is not None else None
    result = {
        "status":       "trained",
        "new_version":  new_version,
        "samples_used": len(X),
        "total_trained": meta["total_trained"],
        "accuracy_before": round(acc_before * 100, 1) if acc_before else None,
        "accuracy_after":  round(acc_after  * 100, 1),
        "improvement":     round(improvement * 100, 2) if improvement else None,
    }

    print(f"[IncrementalTrainer] ✓ Modelo actualizado a v{new_version} con {len(X)} ejemplos nuevos")
    if improvement and improvement > 0:
        print(f"[IncrementalTrainer] Mejora: +{improvement:.1%}")
    elif improvement and improvement < 0:
        print(f"[IncrementalTrainer] Leve bajada en train ({improvement:.1%}) — normal con pocos datos")

    return result


# ── Para prueba manual ────────────────────────────────────────────────────────
if __name__ == "__main__":
    r = run_incremental_training(force=True)
    print(json.dumps(r, indent=2, default=str))
