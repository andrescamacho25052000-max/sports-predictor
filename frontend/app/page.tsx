"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { TrendingUp, Search, Sliders, History, BarChart3 } from "lucide-react";
import Link from "next/link";
import TeamSearch      from "@/components/TeamSearch";
import UpcomingMatches from "@/components/UpcomingMatches";
import CustomMatchForm from "@/components/CustomMatchForm";
import AuthMenu        from "@/components/AuthMenu";
import AuthModal       from "@/components/AuthModal";
import GeneralHistory  from "@/components/GeneralHistory";
import SportSwitcher   from "@/components/SportSwitcher";
import { useAuth }     from "@/lib/auth";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { UpcomingMatch } from "@/lib/api";

interface NavPayload {
  home: string; away: string; league: string;
  date?: string; home_id?: number; away_id?: number;
  home_crest?: string; away_crest?: string;
}

export default function Home() {
  const router = useRouter();
  const { session } = useAuth();
  const [searchQuery, setSearchQuery] = useState("");
  const [showAuth, setShowAuth] = useState(false);

  function goToMatch(p: NavPayload) {
    // Opción B: hay que iniciar sesión para analizar un partido.
    if (!session) {
      setShowAuth(true);
      return;
    }
    const params = new URLSearchParams({
      home: p.home, away: p.away,
      league: p.league ?? "", date: p.date ?? "",
    });
    if (p.home_id)    params.set("homeId",    String(p.home_id));
    if (p.away_id)    params.set("awayId",    String(p.away_id));
    if (p.home_crest) params.set("homeCrest", p.home_crest);
    if (p.away_crest) params.set("awayCrest", p.away_crest);
    router.push(`/match?${params.toString()}`);
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-gray-950 via-gray-900 to-emerald-950 px-4 py-6 sm:py-12 pb-24 sm:pb-12">
      <div className="w-full max-w-5xl mx-auto space-y-5 sm:space-y-8">

        {/* ── Barra superior: track record + sesión ── */}
        <div className="flex items-center justify-end gap-2">
          <Link
            href="/track-record"
            className="flex items-center gap-1.5 text-xs font-medium text-white/60 hover:text-emerald-400 bg-white/5 border border-white/10 rounded-full px-3 py-1.5 transition-colors"
          >
            <BarChart3 size={14} />
            <span className="hidden xs:inline">Track record</span>
          </Link>
          <AuthMenu />
        </div>

        {/* ── Selector de deporte ── */}
        <SportSwitcher />

        {/* ── Header ── */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="text-center space-y-3"
        >
          {/* Logo */}
          <div className="flex items-center justify-center">
            <div className="relative">
              <div className="absolute inset-0 bg-emerald-500/20 rounded-full blur-2xl" />
              <div className="relative bg-gradient-to-br from-emerald-500/30 to-emerald-700/20 border border-emerald-500/30 rounded-2xl p-3 sm:p-4">
                <TrendingUp className="w-7 h-7 sm:w-10 sm:h-10 text-emerald-400" />
              </div>
            </div>
          </div>

          <div className="space-y-1.5">
            <h1 className="text-3xl sm:text-5xl font-black text-white tracking-tight">
              Predictor Deportivo
            </h1>
            <p className="text-gray-400 text-sm sm:text-base max-w-md mx-auto leading-relaxed">
              XGBoost · Elo Rating · Poisson.{" "}
              <span className="text-emerald-400 font-semibold">No adivina — calcula.</span>
            </p>
          </div>

          {/* Stats rápidas */}
          <div className="flex items-center justify-center gap-5 sm:gap-8 pt-1">
            {[
              { label: "Precisión", value: "~67%" },
              { label: "Features", value: "22" },
              { label: "Partidos", value: "3.3k+" },
            ].map(({ label, value }) => (
              <div key={label} className="text-center">
                <div className="text-white font-black text-base sm:text-lg">{value}</div>
                <div className="text-gray-500 text-xs">{label}</div>
              </div>
            ))}
          </div>
        </motion.div>

        {/* ── Panel principal ── */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.15 }}
          className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-3xl p-4 sm:p-6 shadow-2xl"
        >
          {!session && (
            <button
              onClick={() => setShowAuth(true)}
              className="w-full mb-4 text-left bg-emerald-500/10 border border-emerald-500/30 rounded-xl px-4 py-2.5 text-sm text-emerald-300 hover:bg-emerald-500/15 transition-colors"
            >
              🔒 Inicia sesión para analizar partidos y guardar tu historial.
            </button>
          )}

          <Tabs defaultValue="search">
            <TabsList className="w-full mb-4 sm:mb-5">
              <TabsTrigger value="search">
                <Search className="w-4 h-4" />
                <span className="hidden xs:inline">Buscar </span>partido
              </TabsTrigger>
              <TabsTrigger value="custom">
                <Sliders className="w-4 h-4" />
                <span className="hidden xs:inline">Partido </span>personalizado
              </TabsTrigger>
            </TabsList>

            <TabsContent value="search">
              <TeamSearch
                onSelectMatch={(m: UpcomingMatch) => goToMatch(m)}
                onQueryChange={setSearchQuery}
              />
            </TabsContent>

            <TabsContent value="custom">
              <CustomMatchForm onAnalyze={goToMatch} />
            </TabsContent>

          </Tabs>
        </motion.div>

        {/* ── Próximos partidos ── */}
        {searchQuery.trim().length < 2 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.25 }}
            className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-3xl p-4 sm:p-6 shadow-xl"
          >
            <UpcomingMatches onSelectMatch={(m: UpcomingMatch) => goToMatch(m)} />
          </motion.div>
        )}

        {/* ── Historial general (público) ── */}
        {searchQuery.trim().length < 2 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-3xl p-4 sm:p-6 shadow-xl"
          >
            <GeneralHistory />
          </motion.div>
        )}

        <p className="text-center text-gray-700 text-xs pb-2">
          Los mejores modelos del mundo rara vez superan el 65% en fútbol.
        </p>
      </div>

      <AnimatePresence>
        {showAuth && <AuthModal onClose={() => setShowAuth(false)} />}
      </AnimatePresence>

      {/* ── Bottom nav (solo mobile) ── */}
      <nav className="fixed bottom-0 left-0 right-0 sm:hidden bg-gray-950/95 backdrop-blur border-t border-white/10 flex z-50">
        <Link href="/" className="flex-1 flex flex-col items-center gap-1 py-3 text-emerald-400">
          <TrendingUp size={20} />
          <span className="text-xs font-medium">Predecir</span>
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
