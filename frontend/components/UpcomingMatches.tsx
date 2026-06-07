"use client";

import { useState, useEffect } from "react";
import { fetchUpcoming, UpcomingMatch } from "@/lib/api";

interface Props {
  onSelectMatch: (match: UpcomingMatch) => void;
  onLoaded?: (count: number) => void;
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  return d.toLocaleDateString("es-ES", {
    weekday: "short",
    day:     "2-digit",
    month:   "short",
    hour:    "2-digit",
    minute:  "2-digit",
  });
}

export default function UpcomingMatches({ onSelectMatch, onLoaded }: Props) {
  const [matches, setMatches] = useState<UpcomingMatch[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchUpcoming()
      .then(data => {
        setMatches(data);
        onLoaded?.(data.length);
      })
      .catch(() => onLoaded?.(0))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="space-y-4">
        <h2 className="text-lg font-bold text-white">📅 Próximos Partidos</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-white/5 border border-white/10 rounded-2xl p-4 animate-pulse space-y-2">
              <div className="h-3 bg-white/10 rounded w-1/3" />
              <div className="h-4 bg-white/10 rounded w-4/5" />
              <div className="h-3 bg-white/10 rounded w-1/2" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (matches.length === 0) {
    return (
      <div className="space-y-3">
        <h2 className="text-lg font-bold text-white">📅 Próximos Partidos</h2>
        <div className="text-center py-6 space-y-2">
          <p className="text-gray-400 text-sm">
            No hay partidos programados disponibles ahora mismo.
          </p>
          <p className="text-gray-600 text-xs">
            Las ligas europeas reanudan en agosto · Puedes elegir un partido manualmente abajo
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold text-white">📅 Próximos Partidos</h2>
        <span className="text-xs text-gray-500">{matches.length} partidos</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {matches.map((match, i) => (
          <button
            key={i}
            onClick={() => onSelectMatch(match)}
            className="group bg-white/5 border border-white/10 rounded-2xl p-4 text-left hover:bg-white/10 hover:border-emerald-500/40 transition-all duration-200 space-y-3 cursor-pointer w-full"
          >
            <span className="text-xs text-emerald-400/80 font-medium block truncate">
              {match.league}
            </span>

            <div className="flex items-center gap-2">
              <span className="text-white text-sm font-semibold flex-1 text-right leading-tight">
                {match.home}
              </span>
              <span className="text-gray-500 text-xs font-bold flex-shrink-0">vs</span>
              <span className="text-white text-sm font-semibold flex-1 text-left leading-tight">
                {match.away}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-gray-500 text-xs">{formatDate(match.date)}</span>
              <span className="text-emerald-400 text-xs font-semibold group-hover:text-emerald-300 transition-colors">
                Analizar →
              </span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
