"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence } from "framer-motion";
import AuthModal from "@/components/AuthModal";
import GeneralHistory from "@/components/GeneralHistory";
import Hero from "@/components/home/Hero";
import KpiRow from "@/components/home/KpiRow";
import UpcomingStatix from "@/components/home/UpcomingStatix";
import ModelPerformance from "@/components/home/ModelPerformance";
import LeaguesGrid from "@/components/home/LeaguesGrid";
import { useAuth } from "@/lib/auth";
import { UpcomingMatch } from "@/lib/api";

export default function Home() {
  const router = useRouter();
  const { session } = useAuth();
  const [showAuth, setShowAuth] = useState(false);

  function goToMatch(p: UpcomingMatch) {
    // Opción B: hay que iniciar sesión para analizar un partido.
    if (!session) {
      setShowAuth(true);
      return;
    }
    const params = new URLSearchParams({
      home: p.home,
      away: p.away,
      league: p.league ?? "",
      date: p.date ?? "",
    });
    if (p.home_id) params.set("homeId", String(p.home_id));
    if (p.away_id) params.set("awayId", String(p.away_id));
    if (p.home_crest) params.set("homeCrest", p.home_crest);
    if (p.away_crest) params.set("awayCrest", p.away_crest);
    router.push(`/match?${params.toString()}`);
  }

  return (
    <div className="px-4 sm:px-6 py-6 space-y-8 max-w-7xl mx-auto">
      {!session && (
        <button
          onClick={() => setShowAuth(true)}
          className="w-full text-left rounded-xl border border-accent/30 bg-accent/10 px-4 py-2.5 text-sm text-accent hover:bg-accent/15 transition-colors"
        >
          🔒 Inicia sesión para analizar partidos y guardar tu historial.
        </button>
      )}

      <Hero onSelectMatch={goToMatch} onQueryChange={() => {}} />

      <KpiRow />

      <UpcomingStatix onSelectMatch={goToMatch} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
        <ModelPerformance />
        <section className="rounded-3xl border border-border bg-surface p-5 sm:p-6">
          <GeneralHistory />
        </section>
      </div>

      <LeaguesGrid />

      <AnimatePresence>
        {showAuth && <AuthModal onClose={() => setShowAuth(false)} />}
      </AnimatePresence>
    </div>
  );
}
