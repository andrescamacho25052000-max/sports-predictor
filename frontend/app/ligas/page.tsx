"use client";

import { useEffect, useState } from "react";
import { Trophy, ArrowUpRight } from "lucide-react";
import { fetchLeagues, fetchUpcoming, League } from "@/lib/api";

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
    "Brasileirao Serie A": "BRA",
  };
  return map[name] ?? name.slice(0, 3).toUpperCase();
}

export default function LigasPage() {
  const [leagues, setLeagues] = useState<League[] | null>(null);
  const [counts, setCounts] = useState<Record<string, number>>({});

  useEffect(() => {
    let alive = true;
    fetchLeagues()
      .then((l) => alive && setLeagues(l))
      .catch(() => alive && setLeagues([]));
    fetchUpcoming()
      .then((res) => {
        if (!alive) return;
        const c: Record<string, number> = {};
        for (const m of res.matches) c[m.league] = (c[m.league] ?? 0) + 1;
        setCounts(c);
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);

  return (
    <div className="px-4 sm:px-6 py-6 max-w-7xl mx-auto space-y-6">
      <div>
        <p className="eyebrow text-accent">Competiciones</p>
        <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-white mt-1">
          Ligas
        </h1>
        <p className="text-sm text-muted-2 mt-1 max-w-2xl">
          Todas las competiciones cubiertas por el modelo. Explora sus próximos
          partidos y predicciones.
        </p>
      </div>

      {leagues === null ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
          {Array.from({ length: 9 }).map((_, i) => (
            <div
              key={i}
              className="rounded-2xl border border-border bg-surface h-24 animate-pulse"
            />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
          {leagues.map((l) => {
            const n = counts[l.name] ?? 0;
            return (
              <div
                key={l.name}
                className="group flex items-center gap-4 rounded-2xl border border-border bg-surface hover:border-border-strong p-4 transition-colors"
              >
                <span className="grid place-items-center h-12 w-12 rounded-xl bg-accent/15 text-accent shrink-0">
                  <Trophy size={22} />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[10px] font-bold text-muted-2">
                      {code(l.name)}
                    </span>
                    <span className="text-xs text-muted-2 truncate">
                      {l.region}
                    </span>
                  </div>
                  <p className="text-base font-bold text-white truncate">
                    {l.name}
                  </p>
                  <p className="text-xs text-muted-2">
                    {n > 0 ? `${n} partido${n !== 1 ? "s" : ""} próximo${n !== 1 ? "s" : ""}` : "Sin partidos próximos"}
                  </p>
                </div>
                <ArrowUpRight
                  size={18}
                  className="text-muted-2 group-hover:text-accent transition-colors shrink-0"
                />
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
