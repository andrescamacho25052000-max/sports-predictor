"use client";

import { useState, useEffect } from "react";
import { fetchLeagues, fetchMatches, Match, League } from "@/lib/api";

interface AnalyzePayload {
  home: string;
  away: string;
  league: string;
  date?: string;
  home_id?: number;
  away_id?: number;
}

interface Props {
  onAnalyze: (payload: AnalyzePayload) => void;
}

export default function PredictorForm({ onAnalyze }: Props) {
  const [leagues, setLeagues]               = useState<League[]>([]);
  const [selectedLeague, setSelectedLeague] = useState("");
  const [matches, setMatches]               = useState<Match[]>([]);
  const [selectedMatch, setSelectedMatch]   = useState<Match | null>(null);
  const [loadingMatches, setLoadingMatches] = useState(false);
  const [backendDown, setBackendDown]       = useState(false);

  // Cargar ligas al montar
  useEffect(() => {
    fetchLeagues()
      .then(setLeagues)
      .catch(() => setBackendDown(true));
  }, []);

  // Cargar partidos al cambiar de liga
  useEffect(() => {
    if (!selectedLeague) return;
    setSelectedMatch(null);
    setMatches([]);
    setLoadingMatches(true);
    fetchMatches(selectedLeague)
      .then(setMatches)
      .catch(() => {})
      .finally(() => setLoadingMatches(false));
  }, [selectedLeague]);

  const handleAnalyze = () => {
    if (!selectedMatch) return;
    onAnalyze({
      home:    selectedMatch.home,
      away:    selectedMatch.away,
      league:  selectedLeague,
      date:    selectedMatch.date,
      home_id: selectedMatch.home_id,
      away_id: selectedMatch.away_id,
    });
  };

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
    <div className="space-y-5">
      <h2 className="text-lg font-bold text-white">🔍 Buscar partido manualmente</h2>

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
              const found = matches.find(m => `${m.home}|${m.away}` === e.target.value);
              setSelectedMatch(found || null);
            }}
            disabled={!selectedLeague || loadingMatches}
          >
            <option value="" className="bg-gray-900">
              {loadingMatches
                ? "Cargando partidos..."
                : matches.length === 0 && selectedLeague
                ? "Sin partidos programados"
                : "Selecciona un partido..."}
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
        <div className="bg-white/5 rounded-2xl p-4 border border-white/10 flex items-center justify-between">
          <span className="text-white font-bold">{selectedMatch.home}</span>
          <div className="text-center">
            <span className="text-gray-500 text-xs font-bold block">vs</span>
            {selectedMatch.date && (
              <span className="text-gray-600 text-xs">
                {new Date(selectedMatch.date).toLocaleDateString("es-ES", { day: "2-digit", month: "short", year: "numeric" })}
              </span>
            )}
          </div>
          <span className="text-white font-bold">{selectedMatch.away}</span>
        </div>
      )}

      <button
        onClick={handleAnalyze}
        disabled={!selectedMatch}
        className="w-full bg-emerald-500 hover:bg-emerald-400 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-bold py-4 rounded-xl transition-all duration-200 text-base shadow-lg shadow-emerald-500/20 active:scale-95 flex items-center justify-center gap-2"
      >
        Ver análisis
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
        </svg>
      </button>
    </div>
  );
}
