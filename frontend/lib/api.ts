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
}

export async function fetchLeagues(): Promise<string[]> {
  const { data } = await api.get("/leagues");
  return data.leagues;
}

export async function fetchMatches(league: string): Promise<Match[]> {
  const { data } = await api.get(`/leagues/${encodeURIComponent(league)}/matches`);
  return data.matches;
}

export async function fetchPrediction(match: Match, league: string): Promise<Prediction> {
  const { data } = await api.post("/predict", {
    home_team: match.home,
    away_team: match.away,
    home_id: match.home_id,
    away_id: match.away_id,
    league,
  });
  return data;
}
