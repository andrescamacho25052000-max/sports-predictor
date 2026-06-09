import { createClient } from "@supabase/supabase-js";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!;

export const supabase = createClient(url, key);

export type Prediction = {
  id: number;
  created_at: string;
  home_team: string;
  away_team: string;
  league: string | null;
  match_date: string | null;
  home_crest: string | null;
  away_crest: string | null;
  prob_home_win: number | null;
  prob_draw: number | null;
  prob_away_win: number | null;
  pred_winner: string | null;
  confidence: number | null;
  model_used: string | null;
  xg_home: number | null;
  xg_away: number | null;
  result_home_goals: number | null;
  result_away_goals: number | null;
  result_actual: string | null;
  was_correct: boolean | null;
  updated_at: string;
};
