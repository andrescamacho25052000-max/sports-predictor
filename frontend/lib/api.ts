import axios from "axios";

const api = axios.create({ baseURL: "http://localhost:8000" });

export interface Match {
  home: string;
  away: string;
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

export async function fetchPrediction(home: string, away: string): Promise<Prediction> {
  const { data } = await api.post("/predict", { home_team: home, away_team: away });
  return data;
}
