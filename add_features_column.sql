-- Columna para guardar los features usados en cada predicción
-- Permite reentrenar el modelo con datos reales acumulados
ALTER TABLE predictions
  ADD COLUMN IF NOT EXISTS features_json  JSONB,   -- features del modelo en el momento de predecir
  ADD COLUMN IF NOT EXISTS model_version  TEXT,    -- versión del modelo que hizo la predicción
  ADD COLUMN IF NOT EXISTS retrain_used   BOOLEAN DEFAULT FALSE; -- si ya se usó para reentrenar
