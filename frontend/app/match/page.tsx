"use client";

import { useEffect, useRef, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { fetchPrediction, Prediction, Match } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { motion } from "framer-motion";
import ProbabilityBar  from "@/components/ProbabilityBar";
import ValuePanel      from "@/components/ValuePanel";
import ParlaySuggestions from "@/components/ParlaySuggestions";
import { TrendingUp, History, BarChart3, Lock } from "lucide-react";
import Link from "next/link";
import AuthMenu from "@/components/AuthMenu";

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
  const { session, loading: authLoading } = useAuth();

  const home   = sp.get("home")   ?? "";
  const away   = sp.get("away")   ?? "";
  const league = sp.get("league") ?? "";
  const date   = sp.get("date")   ?? "";
  const homeId    = sp.get("homeId") ? Number(sp.get("homeId")) : undefined;
  const awayId    = sp.get("awayId") ? Number(sp.get("awayId")) : undefined;
  const homeCrest = sp.get("homeCrest") ?? undefined;
  const awayCrest = sp.get("awayCrest") ?? undefined;

  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [loading, setLoading]       = useState(true);
  const [error, setError]           = useState("");
  const startedRef = useRef(false);

  useEffect(() => {
    // Esperamos a que la sesión resuelva para atribuir la predicción al usuario.
    if (authLoading || startedRef.current) return;
    if (!home || !away) { router.replace("/"); return; }
    // Opción B: sin sesión no se predice; se muestra la pantalla de login.
    if (!session) { setLoading(false); return; }
    startedRef.current = true;
    const match: Match = { home, away, home_id: homeId, away_id: awayId, date };
    fetchPrediction(match, league, session.access_token)
      .then(setPrediction)
      .catch(() => setError("No se pudo obtener la predicción. ¿El backend está corriendo?"))
      .finally(() => setLoading(false));
  }, [authLoading, session?.access_token]);

  if (!home || !away) return null;

  return (
    <main className="min-h-screen bg-gradient-to-br from-gray-950 via-gray-900 to-emerald-950 px-4 py-5 sm:py-8 pb-24 sm:pb-8">
      <div className="max-w-5xl mx-auto space-y-4 sm:space-y-6">

        {/* ── Nav bar ── */}
        <div className="flex items-center justify-between">
          <button
            onClick={() => router.back()}
            className="flex items-center gap-1.5 text-gray-400 hover:text-white transition-colors text-sm group"
          >
            <svg className="w-4 h-4 group-hover:-translate-x-1 transition-transform" fill="none"
                 viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
            </svg>
            Volver
          </button>
          <a
            href="/history"
            className="hidden sm:flex items-center gap-1.5 text-xs text-white/40 hover:text-emerald-400 transition-colors border border-white/10 hover:border-emerald-500/30 rounded-full px-3 py-1"
          >
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Historial
          </a>
        </div>

        {/* ── Cabecera del partido ── */}
        <motion.div
          initial={{ opacity: 0, y: -16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="relative overflow-hidden bg-gradient-to-br from-gray-800/60 via-gray-900/60 to-emerald-900/30 border border-white/10 rounded-3xl p-4 sm:p-10 text-center shadow-2xl"
        >
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(52,211,153,0.08),transparent_70%)]" />

          {/* liga */}
          {league && (
            <span className="relative inline-block bg-emerald-500/20 text-emerald-400 text-xs font-bold px-3 py-1 rounded-full tracking-wide uppercase mb-3">
              {league}
            </span>
          )}

          {/* equipos */}
          <div className="relative flex items-center justify-between gap-2 sm:gap-8">
            {/* local */}
            <div className="flex-1 flex flex-col items-center gap-2">
              {homeCrest ? (
                <img src={homeCrest} alt={home}
                  className="w-14 h-14 sm:w-20 sm:h-20 object-contain drop-shadow-2xl"
                  onError={(e) => { (e.target as HTMLImageElement).style.display="none"; }} />
              ) : (
                <div className="w-14 h-14 sm:w-20 sm:h-20 rounded-full bg-white/10 border border-white/20 flex items-center justify-center text-xl sm:text-2xl font-black text-white">
                  {home.slice(0,2).toUpperCase()}
                </div>
              )}
              <p className="text-white text-sm sm:text-2xl font-black leading-tight line-clamp-2 text-center">{home}</p>
              <span className="inline-flex items-center gap-1 bg-emerald-500/15 text-emerald-400 text-xs font-semibold px-2 py-1 rounded-full border border-emerald-500/20">
                🏠 <span className="hidden sm:inline">Local</span><span className="sm:hidden">L</span>
              </span>
            </div>

            <div className="flex-shrink-0">
              <span className="text-gray-600 font-black text-2xl sm:text-4xl">VS</span>
            </div>

            {/* visitante */}
            <div className="flex-1 flex flex-col items-center gap-2">
              {awayCrest ? (
                <img src={awayCrest} alt={away}
                  className="w-14 h-14 sm:w-20 sm:h-20 object-contain drop-shadow-2xl"
                  onError={(e) => { (e.target as HTMLImageElement).style.display="none"; }} />
              ) : (
                <div className="w-14 h-14 sm:w-20 sm:h-20 rounded-full bg-white/10 border border-white/20 flex items-center justify-center text-xl sm:text-2xl font-black text-white">
                  {away.slice(0,2).toUpperCase()}
                </div>
              )}
              <p className="text-white text-sm sm:text-2xl font-black leading-tight line-clamp-2 text-center">{away}</p>
              <span className="inline-flex items-center gap-1 bg-indigo-500/15 text-indigo-400 text-xs font-semibold px-2 py-1 rounded-full border border-indigo-500/20">
                ✈️ <span className="hidden sm:inline">Visitante</span><span className="sm:hidden">V</span>
              </span>
            </div>
          </div>

          {/* fecha */}
          {date && (
            <p className="relative text-gray-400 text-xs sm:text-sm capitalize border-t border-white/10 pt-3 mt-3">
              {formatDate(date)}
            </p>
          )}
        </motion.div>

        {/* ── Gate: sin sesión ── */}
        {!authLoading && !session && (
          <div className="bg-white/5 border border-white/10 rounded-3xl p-10 sm:p-14 flex flex-col items-center gap-4 text-center">
            <Lock size={32} className="text-white/30" />
            <div>
              <p className="text-white font-semibold">Inicia sesión para ver esta predicción</p>
              <p className="text-gray-500 text-sm mt-1">El análisis y tu historial requieren una cuenta.</p>
            </div>
            <AuthMenu />
          </div>
        )}

        {/* ── Loading ── */}
        {loading && session && (
          <div className="bg-white/5 border border-white/10 rounded-3xl p-10 sm:p-14 flex flex-col items-center gap-5">
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
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.4 }}
            className="space-y-4 sm:space-y-6"
          >
            {/* probabilidades + factores */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1 }}
              className="bg-white/5 border border-white/10 rounded-3xl p-4 sm:p-6 space-y-6"
            >
              <ProbabilityBar
                homeTeam={prediction.home_team}
                awayTeam={prediction.away_team}
                homeWin={prediction.probabilities.home_win}
                draw={prediction.probabilities.draw}
                awayWin={prediction.probabilities.away_win}
                homeCrest={homeCrest}
                awayCrest={awayCrest}
              />
              <div className="border-t border-white/10 pt-5">
                <ValuePanel
                  probabilities={prediction.probabilities}
                  poisson={prediction.poisson}
                  cornersCards={prediction.corners_cards}
                  odds={prediction.odds}
                  homeTeam={prediction.home_team}
                  awayTeam={prediction.away_team}
                />
              </div>
            </motion.div>

            <p className="text-center text-gray-500 text-xs">
              Modelo: {prediction.model} · Los porcentajes son probabilidades estimadas, no garantías.
            </p>

            <motion.div initial={{ opacity:0, y:20 }} animate={{ opacity:1, y:0 }} transition={{ duration:0.5, delay:0.15 }}>
              <ParlaySuggestions
                probabilities={prediction.probabilities}
                poisson={prediction.poisson}
                cornersCards={prediction.corners_cards}
                homeTeam={prediction.home_team}
                awayTeam={prediction.away_team}
              />
            </motion.div>

            <button
              onClick={() => router.push("/")}
              className="w-full flex items-center justify-center gap-2 bg-white/5 hover:bg-white/10 border border-white/10 hover:border-white/20 text-gray-400 hover:text-white font-medium py-4 rounded-2xl transition-all text-sm"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 12h18M3 12l6-6M3 12l6 6" />
              </svg>
              Analizar otro partido
            </button>
          </motion.div>
        )}

      </div>

      {/* ── Bottom nav (solo mobile) ── */}
      <nav className="fixed bottom-0 left-0 right-0 sm:hidden bg-gray-950/95 backdrop-blur border-t border-white/10 flex z-50">
        <Link href="/" className="flex-1 flex flex-col items-center gap-1 py-3 text-white/40 hover:text-white/70 transition-colors">
          <TrendingUp size={20} />
          <span className="text-xs">Predecir</span>
        </Link>
        <Link href="/track-record" className="flex-1 flex flex-col items-center gap-1 py-3 text-white/40 hover:text-white/70 transition-colors">
          <BarChart3 size={20} />
          <span className="text-xs">Récord</span>
        </Link>
        <Link href="/history" className="flex-1 flex flex-col items-center gap-1 py-3 text-white/40 hover:text-white/70 transition-colors">
          <History size={20} />
          <span className="text-xs">Historial</span>
        </Link>
      </nav>
    </main>
  );
}

export default function MatchPage() {
  return (
    <Suspense>
      <MatchContent />
    </Suspense>
  );
}
