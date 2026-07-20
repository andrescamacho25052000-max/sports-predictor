-- Multiusuario: dueño de cada predicción + Row Level Security
-- (Ya aplicado en producción vía migración add_user_id_and_enable_rls.
--  Se versiona aquí para reproducibilidad.)

-- 1. Columna user_id: dueño de la predicción (null = anónimo o legacy)
ALTER TABLE public.predictions
  ADD COLUMN IF NOT EXISTS user_id uuid REFERENCES auth.users(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_pred_user_id ON public.predictions(user_id);

-- 2. Activar RLS. El backend usa la clave service_role, que BYPASSA RLS,
--    así que sus inserciones y lecturas siguen funcionando sin cambios.
--    RLS solo bloquea el acceso directo con la clave pública (anon) desde
--    el navegador, cerrando una fuga de datos.
ALTER TABLE public.predictions ENABLE ROW LEVEL SECURITY;

-- 3. Política: un usuario autenticado solo puede leer SUS propias predicciones
--    si alguna vez se consulta Supabase directamente desde el cliente.
DROP POLICY IF EXISTS "users select own predictions" ON public.predictions;
CREATE POLICY "users select own predictions"
  ON public.predictions FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);
