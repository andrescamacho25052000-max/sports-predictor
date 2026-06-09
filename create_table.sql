-- Tabla de predicciones del Sports Predictor
CREATE TABLE IF NOT EXISTS predictions (
  id                 BIGSERIAL PRIMARY KEY,
  created_at         TIMESTAMPTZ DEFAULT NOW(),
  home_team          TEXT NOT NULL,
  away_team          TEXT NOT NULL,
  league             TEXT,
  match_date         DATE,
  home_crest         TEXT,
  away_crest         TEXT,

  -- Probabilidades del modelo
  prob_home_win      NUMERIC(5,2),
  prob_draw          NUMERIC(5,2),
  prob_away_win      NUMERIC(5,2),
  pred_winner        TEXT,
  confidence         NUMERIC(5,2),
  model_used         TEXT,

  -- Goles esperados (Poisson)
  xg_home            NUMERIC(4,2),
  xg_away            NUMERIC(4,2),

  -- Resultado real (se llena después del partido)
  result_home_goals  INTEGER,
  result_away_goals  INTEGER,
  result_actual      TEXT,
  was_correct        BOOLEAN,

  updated_at         TIMESTAMPTZ DEFAULT NOW()
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_pred_match_date ON predictions(match_date);
CREATE INDEX IF NOT EXISTS idx_pred_league     ON predictions(league);

-- Trigger: calcula was_correct automáticamente al ingresar resultado
CREATE OR REPLACE FUNCTION update_prediction_result()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.result_actual IS NOT NULL AND NEW.pred_winner IS NOT NULL THEN
    NEW.was_correct = (NEW.result_actual = NEW.pred_winner);
  END IF;
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_prediction_result ON predictions;
CREATE TRIGGER trg_prediction_result
  BEFORE INSERT OR UPDATE ON predictions
  FOR EACH ROW EXECUTE FUNCTION update_prediction_result();

-- Deshabilitar RLS (app personal, no necesita restricciones por usuario)
ALTER TABLE predictions DISABLE ROW LEVEL SECURITY;
