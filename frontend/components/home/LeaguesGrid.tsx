"use client";

import { useEffect, useState } from "react";
import { Trophy } from "lucide-react";
import { fetchLeagues, League } from "@/lib/api";

/** Código corto de una liga para el badge (derivado del nombre). */
function code(name: string): string {
  const map: Record<string, string> = {
    "Premier League": "ENG",
    Championship: "ENG",
    "La Liga": "ESP",
    LaLiga: "ESP",
    Bundesliga: "GER",
    "Serie A": "ITA",
    "Ligue 1": "FRA",
    Eredivisie: "NED",
    "Primeira Liga": "POR",
    "Champions League": "UCL",
    "Copa Libertadores": "CONM",
    "Liga BetPlay": "COL",
    "Mundial FIFA": "FIFA",
  };
  return map[name] ?? name.slice(0, 3).toUpperCase();
}

/**
 * Sección "Ligas principales" (estilo Statix): grid de ligas reales cubiertas
 * por el backend.
 */
export default function LeaguesGrid() {
  const [leagues, setLeagues] = useState<League[] | null>(null);

  useEffect(() => {
    let alive = true;
    fetchLeagues()
      .then((l) => alive && setLeagues(l))
      .catch(() => alive && setLeagues([]));
    return () => {
      alive = false;
    };
  }, []);

  return (
    <section className="space-y-4">
      <div className="flex items-center gap-2.5">
        <span className="grid place-items-center h-9 w-9 rounded-xl bg-accent/15 text-accent">
          <Trophy size={18} />
        </span>
        <div>
          <h2 className="text-lg font-bold text-white">Ligas principales</h2>
          <p className="text-xs text-muted-2">Cobertura por competición</p>
        </div>
      </div>

      {leagues === null ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
          {Array.from({ length: 8 }).map((_, i) => (
            <div
              key={i}
              className="rounded-2xl border border-border bg-surface h-16 animate-pulse"
            />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
          {leagues.map((l) => (
            <div
              key={l.name}
              className="flex items-center gap-3 rounded-2xl border border-border bg-surface px-4 py-3"
            >
              <span className="grid place-items-center h-9 w-11 rounded-lg bg-surface-2 border border-border font-mono text-[10px] font-bold text-muted shrink-0">
                {code(l.name)}
              </span>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-white truncate">
                  {l.name}
                </p>
                <p className="text-xs text-muted-2 truncate">{l.region}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
