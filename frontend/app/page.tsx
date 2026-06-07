"use client";

import { useState, useRef } from "react";
import PredictorForm from "@/components/PredictorForm";
import UpcomingMatches from "@/components/UpcomingMatches";
import { UpcomingMatch } from "@/lib/api";

export default function Home() {
  const [preselected, setPreselected] = useState<UpcomingMatch | null>(null);
  const formRef = useRef<HTMLDivElement>(null);

  function handleSelectMatch(match: UpcomingMatch) {
    setPreselected({ ...match }); // new object reference so useEffect fires even for same match
    setTimeout(() => {
      formRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 80);
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-gray-950 via-gray-900 to-emerald-950 flex flex-col items-center justify-start px-4 py-12">
      <div className="w-full max-w-2xl space-y-8">

        {/* Header */}
        <div className="text-center space-y-3">
          <div className="text-5xl">⚽</div>
          <h1 className="text-4xl font-black text-white tracking-tight">
            Predictor Deportivo
          </h1>
          <p className="text-gray-400 text-base max-w-md mx-auto">
            Análisis estadístico de partidos basado en forma reciente, plantel, localía y más. No adivina — calcula.
          </p>
        </div>

        {/* Próximos partidos */}
        <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-3xl p-6 shadow-2xl">
          <UpcomingMatches onSelectMatch={handleSelectMatch} />
        </div>

        {/* Predictor */}
        <div ref={formRef} className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-3xl p-6 shadow-2xl scroll-mt-8">
          <PredictorForm preselected={preselected} />
        </div>

        <p className="text-center text-gray-600 text-xs">
          Incluso los mejores modelos rara vez superan el 65% de precisión en fútbol. El deporte tiene mucho ruido.
        </p>
      </div>
    </main>
  );
}
