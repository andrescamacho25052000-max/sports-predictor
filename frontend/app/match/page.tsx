"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { fetchPrediction, Prediction, Match } from "@/lib/api";
import ProbabilityBar  from "@/components/ProbabilityBar";
import FactorsList     from "@/components/FactorsList";
import TeamStats       from "@/components/TeamStats";
import MatchContext    from "@/components/MatchContext";

function formatDate(d: string) {
  if (!d) return "";
  return new Date(d).toLocaleDateString("es-ES", {
    weekday: "long", day: "2-digit", month: "long",
    year: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

/* ─── contenido de la página ─── */
function MatchContent() {
  const router = useRouter();
  const sp     = useSearchParams();

  const home   = sp.get("home")   ?? "";
  const away   = sp.get("away")   ?? "";
  const league = sp.get("league") ?? "";
  const date   = sp.get("date")   ?? "";
  const homeId = sp.get("homeId") ? Number(sp.get("homeId")) : undefined;
  const awayId = sp.get("awayId") ? Number(sp.get("awayId")) : undefined;

  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [loading, setLoading]       = useState(true);
  const [error, setError]           = useState("");

  useEffect(() => {
    if (!home || !away) { router.replace("/"); return; }
    const match: Match = { home, away, home_id: homeId, away_id: awayId, date };
    fetchPrediction(match, league)
      .then(setPrediction)
      .catch(() => setError("No se pudo obtener la predicción. ¿El backend está corriendo?"))
      .finally(() => setLoading(false));
  }, []);

  if (!home || !away) return null;

  return (
    <main className="min-h-screen bg-gradient-to-br from-gray-950 via-gray-900 to-emerald-950 px-4 py-8">
      <div className="max-w-2xl mx-auto space-y-6">

        {/* ── Botón volver ── */}
        <button
          onClick={() => router.back()}
          className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors text-sm group"
        >
          <svg className="w-4 h-4 group-hover:-translate-x-1 transition-transform" fill="none"
               viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
          Volver
        </button>

        {/* ── Cabecera del partido ── */}
        <div className="relative overflow-hidden bg-gradient-to-br from-gray-800/60 via-gray-900/60 to-emerald-900/30 border border-white/10 rounded-3xl p-6 sm:p-10 text-center space-y-6 shadow-2xl">
          {/* fondo decorativo */}
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(52,211,153,0.06),transparent_70%)]" />

          {/* liga */}
          {league && (
            <span className="relative inline-block bg-emerald-500/20 text-emerald-400 text-xs font-bold px-4 py-1.5 rounded-full tracking-wide uppercase">
              {league}
            </span>
          )}

          {/* equipos */}
          <div className="relative flex items-center justify-between gap-2 sm:gap-6">
            {/* local */}
            <div className="flex-1 space-y-3">
              <p className="text-white text-xl sm:text-3xl font-black leading-tight">
                {home}
              </p>
              <span className="inline-flex items-center gap-1.5 bg-white/10 text-gray-300 text-xs font-medium px-3 py-1.5 rounded-full">
                🏠 Local
              </span>
            </div>

            <div className="flex-shrink-0 text-gray-600 font-black text-2xl sm:text-3xl">VS</div>

            {/* visitante */}
            <div className="flex-1 space-y-3">
              <p className="text-white text-xl sm:text-3xl font-black leading-tight">
                {away}
              </p>
              <span className="inline-flex items-center gap-1.5 bg-white/10 text-gray-300 text-xs font-medium px-3 py-1.5 rounded-full">
                ✈️ Visitante
              </span>
            </div>
          </div>

          {/* fecha */}
          {date && (
            <p className="relative text-gray-400 text-sm capitalize border-t border-white/10 pt-4">
              {formatDate(date)}
            </p>
          )}
        </div>

        {/* ── Loading ── */}
        {loading && (
          <div className="bg-white/5 border border-white/10 rounded-3xl p-14 flex flex-col items-center gap-5">
            <div className="relative">
              <div className="absolute inset-0 rounded-full bg-emerald-400/20 animate-ping" />
              <svg className="relative animate-spin h-10 w-10 text-emerald-400" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                <path className="opacity-80" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
              </svg>
            </div>
            <div className="text-center space-y-1">
              <p className="text-white font-semibold">Analizando el partido</p>
              <p className="text-gray-500 text-sm">Consultando estadísticas, clima y lesionados…</p>
            </div>
          </div>
        )}

        {/* ── Error ── */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-2xl p-5 text-center space-y-3">
            <p className="text-red-400 font-semibold">{error}</p>
            <button
              onClick={() => router.push("/")}
              className="text-sm text-gray-400 hover:text-white underline underline-offset-2 transition"
            >
              Volver al inicio
            </button>
          </div>
        )}

        {/* ── Resultados ── */}
        {prediction && !loading && (
          <div className="space-y-6">

            {/* probabilidades + factores */}
            <div className="bg-white/5 border border-white/10 rounded-3xl p-6 space-y-6">
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

            {/* estadísticas */}
            {prediction.team_stats && (
              <TeamStats
                home={prediction.team_stats.home}
                away={prediction.team_stats.away}
                homeTeam={prediction.home_team}
                awayTeam={prediction.away_team}
              />
            )}

            {/* contexto: estadio / clima / lesionados */}
            <MatchContext
              stadium={prediction.stadium}
              weather={prediction.weather}
              injuries={prediction.injuries}
            />

            {/* botón de retorno */}
            <button
              onClick={() => router.push("/")}
              className="w-full flex items-center justify-center gap-2 bg-white/5 hover:bg-white/10 border border-white/10 hover:border-white/20 text-gray-400 hover:text-white font-medium py-4 rounded-2xl transition-all text-sm"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 12h18M3 12l6-6M3 12l6 6" />
              </svg>
              Analizar otro partido
            </button>
          </div>
        )}

      </div>
    </main>
  );
}

/* Suspense obligatorio para useSearchParams en Next.js App Router */
export default function MatchPage() {
  return (
    <Suspense>
      <MatchContent />
    </Suspense>
  );
}
