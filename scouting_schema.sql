-- ============================================================================
-- BASE DE DATOS DE RECOLECCION (scouting_*)
-- Tablas con prefijo scouting_ para separarlas de las predicciones (public.predictions).
-- Correr UNA VEZ en Supabase -> SQL Editor -> pegar todo -> Run.
-- ============================================================================

-- 🟢 NIVEL 1 — NUCLEO -----------------------------------------------------------

create table if not exists public.scouting_teams (
  id            bigserial primary key,
  name          text not null unique,
  type          text not null default 'national',   -- national | club
  country       text,
  aliases       jsonb default '[]'::jsonb,           -- nombres alternativos (cruce de fuentes)
  external_ids  jsonb default '{}'::jsonb,
  crest_url     text,
  created_at    timestamptz default now()
);

create table if not exists public.scouting_matches (
  id               bigserial primary key,
  source           text,
  source_url       text,
  collected_at     timestamptz default now(),
  competition_type text default 'national',          -- national | club
  category         text,                             -- mundial | eliminatoria | continental | amistoso | otro
  tournament       text,
  season           text,
  match_date       date,
  kickoff_utc      timestamptz,
  home_team_id     bigint references public.scouting_teams(id),
  away_team_id     bigint references public.scouting_teams(id),
  home_team        text,
  away_team        text,
  home_goals       int,
  away_goals       int,
  winner           text,                             -- Local | Empate | Visitante
  ht_home_goals    int,
  ht_away_goals    int,
  neutral          boolean,
  stadium          text,
  city             text,
  country          text,
  attendance       int,
  referee          text,
  -- Clima (enriquecimiento posterior via Open-Meteo archive)
  temp_c           numeric,
  feels_like_c     numeric,                          -- sensacion termica
  precip_mm        numeric,
  wind_kmh         numeric,
  weather_desc     text,
  external_ids     jsonb default '{}'::jsonb,
  raw              jsonb,                             -- volcado crudo de la fuente (guardar TODO)
  created_at       timestamptz default now(),
  unique (tournament, match_date, home_team, away_team)
);
create index if not exists idx_scout_match_date on public.scouting_matches(match_date);
create index if not exists idx_scout_match_cat  on public.scouting_matches(category);
create index if not exists idx_scout_match_tour on public.scouting_matches(tournament);

create table if not exists public.scouting_match_team_stats (
  id                 bigserial primary key,
  match_id           bigint references public.scouting_matches(id) on delete cascade,
  team_id            bigint references public.scouting_teams(id),
  is_home            boolean,
  possession         numeric,
  shots              int,
  shots_on_target    int,
  shots_off_target   int,
  blocked_shots      int,
  xg                 numeric,                         -- goles esperados (el mas predictivo)
  corners            int,
  fouls_committed    int,
  fouls_drawn        int,
  offsides           int,
  yellow_cards       int,
  red_cards          int,
  passes             int,
  passes_completed   int,
  pass_accuracy      numeric,
  crosses            int,
  tackles            int,
  interceptions      int,
  clearances         int,
  saves              int,
  big_chances        int,
  big_chances_missed int,
  touches_in_box     int,
  errors_to_shot     int,
  errors_to_goal     int,
  raw                jsonb,
  created_at         timestamptz default now()
);
create index if not exists idx_scout_mts_match on public.scouting_match_team_stats(match_id);

-- 🟡 NIVEL 2 — CONTEXTO ---------------------------------------------------------

create table if not exists public.scouting_players (
  id            bigserial primary key,
  name          text not null,
  aliases       jsonb default '[]'::jsonb,
  birthdate     date,
  nationality   text,
  position      text,
  external_ids  jsonb default '{}'::jsonb,
  created_at    timestamptz default now()
);

create table if not exists public.scouting_lineups (
  id             bigserial primary key,
  match_id       bigint references public.scouting_matches(id) on delete cascade,
  team_id        bigint references public.scouting_teams(id),
  player_id      bigint references public.scouting_players(id),
  role           text,                               -- titular | suplente
  position       text,
  shirt_number   int,
  minutes_played int,
  subbed_in_min  int,
  subbed_out_min int,
  is_captain     boolean,
  raw            jsonb
);
create index if not exists idx_scout_lineup_match on public.scouting_lineups(match_id);

create table if not exists public.scouting_match_events (
  id                bigserial primary key,
  match_id          bigint references public.scouting_matches(id) on delete cascade,
  team_id           bigint references public.scouting_teams(id),
  player_id         bigint references public.scouting_players(id),
  related_player_id bigint references public.scouting_players(id),  -- asistencia / a quien reemplaza
  minute            int,
  extra_minute      int,
  event_type        text,   -- goal | own_goal | penalty_goal | penalty_miss | yellow | red | sub | var
  detail            jsonb,
  raw               jsonb
);
create index if not exists idx_scout_event_match on public.scouting_match_events(match_id);

create table if not exists public.scouting_match_odds (
  id           bigserial primary key,
  match_id     bigint references public.scouting_matches(id) on delete cascade,
  bookmaker    text,
  market       text,                                 -- 1x2 | over_under | handicap
  odds         jsonb,
  is_closing   boolean,
  collected_at timestamptz default now()
);

-- 🔵 NIVEL 3 — GRANULAR / TECNICO ----------------------------------------------

create table if not exists public.scouting_player_match_stats (
  id                  bigserial primary key,
  match_id            bigint references public.scouting_matches(id) on delete cascade,
  team_id             bigint references public.scouting_teams(id),
  player_id           bigint references public.scouting_players(id),
  minutes             int,
  goals               int,
  assists             int,
  shots               int,
  shots_on_target     int,
  xg                  numeric,
  xa                  numeric,                        -- asistencias esperadas
  passes              int,
  passes_completed    int,
  key_passes          int,
  pass_accuracy       numeric,
  dribbles            int,
  tackles             int,
  interceptions       int,
  duels_won           int,
  fouls               int,
  fouled              int,
  rating              numeric,
  touches             int,
  possession_lost     int,
  -- Datos tipo tracking (rara vez gratis; columnas listas por si aparecen)
  distance_covered_km numeric,
  sprints             int,
  top_speed_kmh       numeric,
  raw                 jsonb,
  created_at          timestamptz default now()
);
create index if not exists idx_scout_pms_match on public.scouting_player_match_stats(match_id);

-- Seguridad: RLS activado sin politicas -> solo el backend (service_role) accede.
alter table public.scouting_teams             enable row level security;
alter table public.scouting_matches           enable row level security;
alter table public.scouting_match_team_stats  enable row level security;
alter table public.scouting_players           enable row level security;
alter table public.scouting_lineups           enable row level security;
alter table public.scouting_match_events       enable row level security;
alter table public.scouting_match_odds         enable row level security;
alter table public.scouting_player_match_stats enable row level security;
