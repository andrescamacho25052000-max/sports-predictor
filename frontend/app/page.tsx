"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import TeamSearch      from "@/components/TeamSearch";
import UpcomingMatches from "@/components/UpcomingMatches";
import { UpcomingMatch } from "@/lib/api";

interface NavPayload {
  home: string; away: string; league: string;
  date?: string; home_id?: number; away_id?: number;
}

export default function Home() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState("");

  function goToMatch(p: NavPayload) {
    const params = new URLSearchParams({ home: p.home, away: p.away, league: p.league, date: p.date ?? "" });
    if (p.home_id) params.set("homeId", String(p.home_id));
    if (p.away_id) params.set("awayId", String(p.away_id));
    router.push(`/match?${params.toString()}`);
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-gray-950 via-gray-900 to-emerald-950 flex flex-col items-center justify-start px-4 py-12">
      <div className="w-full max-w-2xl space-y-8">

        {/* ── Header ── */}
        <div className="text-center space-y-3">
          <div className="text-5xl">⚽</div>
          <h1 className="text-4xl font-black text-white tracking-tight">Predictor Deportivo</h1>
          <p className="text-gray-400 text-base max-w-md mx-auto">
            Análisis estadístico basado en forma, plantel, localía y más.{" "}
            <span className="text-emerald-400 font-medium">No adivina — calcula.</span>
          </p>
        </div>

        {/* ── Buscador (siempre arriba) ── */}
        <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-3xl p-6 shadow-xl">
          <TeamSearch
            onSelectMatch={(m: UpcomingMatch) => goToMatch(m)}
            onQueryChange={setSearchQuery}
          />
        </div>

        {/* ── Próximos partidos (solo cuando no hay búsqueda activa) ── */}
        {searchQuery.trim().length < 2 && (
          <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-3xl p-6 shadow-xl">
            <UpcomingMatches onSelectMatch={(m: UpcomingMatch) => goToMatch(m)} />
          </div>
        )}

        <p className="text-center text-gray-600 text-xs">
          Incluso los mejores modelos rara vez superan el 65% de precisión en fútbol. El deporte tiene mucho ruido.
        </p>
      </div>
    </main>
  );
}
