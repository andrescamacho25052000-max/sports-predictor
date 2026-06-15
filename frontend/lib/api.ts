import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const api = axios.create({ baseURL: API_URL });

export interface Match {
  home: string;
  away: string;
  home_id?: number;
  away_id?: number;
  date?: string;
  home_crest?: string;
  away_crest?: string;
}

export interface Factor {
  name: string;
  weight: number;
  advantage: string;
  detail: string;
}

export interface RecentMatch {
  opponent: string;
  goals_for: number;
  goals_against: number;
  result: "V" | "E" | "D";
  was_home: boolean;
  date: string;
}

export interface TeamData {
  ranking: number;
  league: string;
  recent_matches: RecentMatch[];
}

export interface InjuredPlayer {
  name: string;
  reason: string;
  photo?: string;
}

export interface Stadium {
  name: string;
  city: string;
  capacity?: number;
  surface?: string;
  image?: string;
  home_team_logo?: string;
}

export interface Weather {
  city: string;
  date: string;
  temp_max: number;
  temp_min: number;
  precipitation: number;
  windspeed: number;
  description: string;
  emoji: string;
  impact: string;
}

export interface PoissonData {
  expected_goals:   { home: number; away: number; total: number };
  result_1x2:       { home_win: number; draw: number; away_win: number };
  over_under:       Record<string, number>;
  btts:             { yes: number; no: number };
  exact_score:      { score: string; home: number; away: number; prob: number }[];
  half_time:        { home_win: number; draw: number; away_win: number };
  handicap?:        Record<string, number>;
  home_goals:       Record<string, number>;
  away_goals:       Record<string, number>;
  home_clean_sheet: { yes: number; no: number };
  away_clean_sheet: { yes: number; no: number };
}

export interface CornerCardsData {
  data_source: "statsbomb" | "global_average";
  corners: {
    expected_home: number;
    expected_away: number;
    expected_total: number;
    over_under: Record<string, number>;
    home_more: number;
    away_more: number;
    equal: number;
  };
  yellow_cards: {
    expected_home: number;
    expected_away: number;
    expected_total: number;
    over_under: Record<string, number>;
    home_dist: Record<string, number>;
    away_dist: Record<string, number>;
  };
  fouls: {
    expected_home: number;
    expected_away: number;
    expected_total: number;
  };
}

export interface Prediction {
  home_team: string;
  away_team: string;
  probabilities: {
    home_win: number;
    draw: number;
    away_win: number;
  };
  factors: Factor[];
  model: string;
  poisson?: PoissonData;
  corners_cards?: CornerCardsData;
  team_stats?: {
    home: TeamData;
    away: TeamData;
  };
  injuries?: {
    home: { team: string; players: InjuredPlayer[] };
    away: { team: string; players: InjuredPlayer[] };
  };
  stadium?: Stadium;
  weather?: Weather;
}

export interface League {
  name: string;
  region: string;
}

export interface UpcomingMatch extends Match {
  league: string;
}

export async function fetchLeagues(): Promise<League[]> {
  const { data } = await api.get("/leagues");
  return data.leagues;
}

export interface UpcomingResponse {
  matches: UpcomingMatch[];
  betplay_quota: { exhausted: boolean; remaining: number | null };
}

export async function fetchUpcoming(): Promise<UpcomingResponse> {
  const { data } = await api.get("/upcoming");
  return data;
}

export async function fetchMatches(league: string): Promise<Match[]> {
  const { data } = await api.get(`/leagues/${encodeURIComponent(league)}/matches`);
  return data.matches;
}

export interface BetSlipLeg {
  match: string;
  market: string;
  prob: number;
  min_odds: number;
  note?: string;
}

export interface BetSlipAnalysis {
  legs: BetSlipLeg[];
  combined_prob: number;
  fair_odds: number;
  offered_odds: number | null;
  value: "negativo" | "justo" | "positivo";
  verdict: string;
  weakest_leg?: string;
  stake?: number | null;
}

export async function analyzeBetSlip(imageBase64: string, mediaType: string): Promise<BetSlipAnalysis> {
  const { data } = await api.post("/analyze-bet-slip", {
    image: imageBase64,
    media_type: mediaType,
  }, { timeout: 120000 });
  return data;
}

export async function fetchPrediction(match: Match, league: string): Promise<Prediction> {
  const { data } = await api.post("/predict", {
    home_team:  match.home,
    away_team:  match.away,
    home_id:    match.home_id,
    away_id:    match.away_id,
    match_date: match.date,
    league,
  });
  return data;
}
