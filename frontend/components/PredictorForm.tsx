"use client";

import { useState, useEffect } from "react";
import { fetchLeagues, fetchMatches, fetchPrediction, Match, Prediction, League } from "@/lib/api";
import ProbabilityBar from "./ProbabilityBar";
import FactorsList from "./FactorsList";
import TeamStats from "./TeamStats";
import MatchContext from "./MatchContext";

export default function PredictorForm() {
  const [leagues, setLeagues]           = useState<League[]>([]);
  const [selectedLeague, setSelectedLeague] = useState("");
  const [matches, setMatches]           = useState<Match[]>([]);
  const [selectedMatch, setSelectedMatch]   = useState<Match | null>(null);
  const [prediction, setPrediction]     = useState<Prediction | null>(null);
  const [loading, setLoading]           = useState(false);
  const [loadingMatches, setLoadingMatches] = useState(false);
  const [error, setError]               = useState("");
  const [backendDown, setBackendDown]   = useState(false);

  useEffect(() => {
    fetchLeagues()
      .then(setLeagues)
      .catch(() => setBackendDown(true));
  }, []);

  useEffect(() => {
    if (!selectedLeague) return;
    setSelectedMatch(null);
    setPrediction(null);
    setMatches([]);
    setLoadingMatches(true);
    fetchMatches(selectedLeague)
      .then(setMatches)
      .catch(() => setError("Error al cargar partidos"))
      .finally(() => setLoadingMatches(false));
  }, [selectedLeague]);

  const handleAnalyze = async () => {
    if (!selectedMatch) return;
    setLoading(true);
    setError("");
    setPrediction(null);
    try {
      const result = await fetchPrediction(selectedMatch, selectedLeague);
      setPrediction(result);
    } catch {
      setError("Error al obtener predicción. ¿El backend está corriendo?");
    } finally {
      setLoading(false);
    }
  };

  // Agrupar ligas por región
  const leaguesByRegion = leagues.reduce<Record<string, League[]>>((acc, l) => {
    if (!acc[l.region]) acc[l.region] = [];
    acc[l.region].push(l);
    return acc;
  }, {});

  if (backendDown) {
    return (
      <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-2xl p-6 text-center space-y-2">
        <p className="text-yellow-400 font-semibold">Backend no disponible</p>
        <p className="text-gray-400 text-sm">Ejecuta el backend primero:</p>
        <code className="bg-black/40 text-green-400 text-xs px-3 py-2 rounded-lg block">
          cd backend && uvicorn main:app --reload
        </code>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Selectors */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">

        {/* Liga */}
        <div className="space-y-2">
          <label className="text-sm text-gray-400 font-medium">Liga / Competición</label>
          <select
            className="w-full bg-white/10 border border-white/20 rounded-xl px-4 py-3 text-white appearance-none cursor-pointer hover:bg-white/15 transition focus:outline-none focus:ring-2 focus:ring-emerald-500"
            value={selectedLeague}
            onChange={(e) => setSelectedLeague(e.target.value)}
          >
            <option value="" className="bg-gray-900">Selecciona una competición...</option>
            {Object.entries(leaguesByRegion).map(([region, ls]) => (
              <optgroup key={region} label={region} className="bg-gray-900 text-gray-400">
                {ls.map((l) => (
                  <option key={l.name} value={l.name} className="bg-gray-900 text-white">
                    {l.name}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
        </div>

        {/* Partido */}
        <div className="space-y-2">
          <label className="text-sm text-gray-400 font-medium">Partido</label>
          <select
            className="w-full bg-white/10 border border-white/20 rounded-xl px-4 py-3 text-white appearance-none cursor-pointer hover:bg-white/15 transition focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:opacity-40 disabled:cursor-not-allowed"
            value={selectedMatch ? `${selectedMatch.home}|${selectedMatch.away}` : ""}
            onChange={(e) => {
              const found = matches.find((m) => `${m.home}|${m.away}` === e.target.value);
              setSelectedMatch(found || null);
              setPrediction(null);
            }}
            disabled={!selectedLeague || loadingMatches}
          >
            <option value="" className="bg-gray-900">
              {loadingMatches ? "Cargando partidos..." : matches.length === 0 && selectedLeague ? "Sin partidos programados" : "Selecciona un partido..."}
            </option>
            {matches.map((m) => (
              <option key={`${m.home}|${m.away}`} value={`${m.home}|${m.away}`} className="bg-gray-900">
                {m.home} vs {m.away}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Partido seleccionado */}
      {selectedMatch && (
        <div className="bg-white/5 rounded-2xl p-4 border border-white/10">
          <div className="flex items-center justify-between">
            <span className="text-white font-bold text-lg">{selectedMatch.home}</span>
            <div className="text-center">
              <span className="text-gray-400 text-sm font-medium block">vs</span>
              {selectedMatch.date && (
                <span className="text-gray-500 text-xs">
                  {new Date(selectedMatch.date).toLocaleDateString("es-ES", { day: "2-digit", month: "short", year: "numeric" })}
                </span>
              )}
            </div>
            <span className="text-white font-bold text-lg">{selectedMatch.away}</span>
          </div>
        </div>
      )}

      {/* Botón analizar */}
      <button
        onClick={handleAnalyze}
        disabled={!selectedMatch || loading}
        className="w-full bg-emerald-500 hover:bg-emerald-400 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-bold py-4 rounded-xl transition-all duration-200 text-lg shadow-lg shadow-emerald-500/20 active:scale-95"
      >
        {loading ? (
          <span className="flex items-center justify-center gap-2">
            <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
            Analizando...
          </span>
        ) : "Analizar"}
      </button>

      {/* Error */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-3 text-red-400 text-sm text-center">
          {error}
        </div>
      )}

      {/* Resultado */}
      {prediction && (
        <div className="space-y-6">
          <div className="bg-white/5 border border-white/10 rounded-2xl p-6 space-y-6">
            <ProbabilityBar
              homeTeam={prediction.home_team}
              awayTeam={prediction.away_team}
              homeWin={prediction.probabilities.home_win}
              draw={prediction.probabilities.draw}
              awayWin={prediction.probabilities.away_win}
            />
            <div className="border-t border-white/10 pt-6">
              <FactorsList
                factors={prediction.factors}
                homeTeam={prediction.home_team}
                awayTeam={prediction.away_team}
              />
            </div>
          </div>

          <p className="text-center text-gray-500 text-xs">
            Modelo: {prediction.model} · Los porcentajes son probabilidades estimadas, no garantías.
          </p>

          {prediction.team_stats && (
            <TeamStats
              home={prediction.team_stats.home}
              away={prediction.team_stats.away}
              homeTeam={prediction.home_team}
              awayTeam={prediction.away_team}
            />
          )}

          <MatchContext
            stadium={prediction.stadium}
            weather={prediction.weather}
            injuries={prediction.injuries}
          />
        </div>
      )}
    </div>
  );
}
