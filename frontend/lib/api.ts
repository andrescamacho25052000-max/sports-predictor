import axios from "axios";

const api = axios.create({ baseURL: "http://localhost:8000" });

export interface Match {
  home: string;
  away: string;
  home_id?: number;
  away_id?: number;
  date?: string;
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

export async function fetchLeagues(): Promise<League[]> {
  const { data } = await api.get("/leagues");
  return data.leagues;
}

export async function fetchMatches(league: string): Promise<Match[]> {
  const { data } = await api.get(`/leagues/${encodeURIComponent(league)}/matches`);
  return data.matches;
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
