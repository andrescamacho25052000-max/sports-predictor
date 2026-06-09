-- Agregar IDs de equipos para poder consultar resultados automáticamente
ALTER TABLE predictions
  ADD COLUMN IF NOT EXISTS fd_home_id   INTEGER,   -- football-data.org team ID
  ADD COLUMN IF NOT EXISTS fd_away_id   INTEGER,   -- football-data.org team ID
  ADD COLUMN IF NOT EXISTS fd_match_id  INTEGER,   -- football-data.org match ID (para lookup directo)
  ADD COLUMN IF NOT EXISTS auto_updated BOOLEAN DEFAULT FALSE;  -- resultado cargado automáticamente
