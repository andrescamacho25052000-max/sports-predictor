"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import TeamSearch from "@/components/TeamSearch";
import { UpcomingMatch } from "@/lib/api";

/**
 * Hero de la home (estilo Statix): badge de modelos activos, titular con acento
 * en gradiente, buscador global y dos CTAs.
 */
export default function Hero({
  onSelectMatch,
  onQueryChange,
}: {
  onSelectMatch: (m: UpcomingMatch) => void;
  onQueryChange: (q: string) => void;
}) {
  return (
    <motion.section
      initial={{ opacity: 0, y: -12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="relative overflow-hidden rounded-3xl border border-border bg-surface p-6 sm:p-10"
    >
      {/* Glow decorativo */}
      <div className="pointer-events-none absolute -top-24 -left-16 h-64 w-64 rounded-full bg-accent/15 blur-3xl" />
      <div className="pointer-events-none absolute -top-10 right-10 h-40 w-40 rounded-full bg-accent-2/10 blur-3xl" />

      <div className="relative space-y-5">
        <span className="inline-flex items-center gap-2 rounded-full border border-border bg-surface-2 px-3 py-1.5 text-xs text-muted">
          <span className="h-1.5 w-1.5 rounded-full bg-accent" />
          <span className="font-medium text-white/80">Modelos activos</span>
          <span className="text-muted-2">·</span>
          <span className="font-mono text-[11px] text-muted-2">
            XGBoost · Elo · Dixon-Coles · Poisson · ML
          </span>
        </span>

        <h1 className="text-3xl sm:text-5xl font-black tracking-tight text-white max-w-3xl leading-[1.05]">
          Inteligencia deportiva basada en{" "}
          <span className="bg-gradient-to-r from-accent to-accent-2 bg-clip-text text-transparent">
            datos y probabilidad
          </span>
        </h1>

        <p className="text-muted text-sm sm:text-base max-w-2xl leading-relaxed">
          Analizamos miles de partidos con modelos matemáticos avanzados para
          calcular probabilidades reales — no adivinamos resultados,
          cuantificamos escenarios.
        </p>

        {/* Buscador global */}
        <div className="max-w-2xl">
          <TeamSearch onSelectMatch={onSelectMatch} onQueryChange={onQueryChange} />
        </div>

        {/* CTAs */}
        <div className="flex flex-wrap items-center gap-3 pt-1">
          <a
            href="#proximos"
            className="inline-flex items-center gap-1.5 rounded-xl bg-accent px-4 py-2.5 text-sm font-semibold text-black hover:bg-accent-strong transition-colors"
          >
            Ver partidos de hoy
            <ArrowUpRight size={16} />
          </a>
          <Link
            href="/predicciones"
            className="inline-flex items-center gap-1.5 rounded-xl border border-border bg-surface-2 px-4 py-2.5 text-sm font-medium text-white hover:border-border-strong transition-colors"
          >
            Explorar predicciones IA
          </Link>
        </div>
      </div>
    </motion.section>
  );
}
