-- Campos de carrera para la tabla de jugadores (tipo tarjeta FIFA/EA FC).
-- Correr UNA VEZ en Supabase -> SQL Editor -> Run.

ALTER TABLE public.scouting_players
  ADD COLUMN IF NOT EXISTS national_team text,   -- seleccion
  ADD COLUMN IF NOT EXISTS current_club  text,   -- equipo actual (se llena luego)
  ADD COLUMN IF NOT EXISTS career_stats  jsonb DEFAULT '{}'::jsonb;  -- goles, penales, etc.

-- Nombre unico para poder actualizar (upsert) sin duplicar.
CREATE UNIQUE INDEX IF NOT EXISTS uq_scouting_players_name
  ON public.scouting_players(name);
