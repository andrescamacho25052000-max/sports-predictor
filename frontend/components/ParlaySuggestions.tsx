"use client";

import { useMemo, useState } from "react";
import { Layers, Wand2, Plus, Check } from "lucide-react";
import { PoissonData, CornerCardsData } from "@/lib/api";
import { buildMarketRows, topExactScores, minOdds, CATEGORY_COLORS, MarketRow } from "@/lib/markets";
import { cn } from "@/lib/utils";

interface Props {
  probabilities: { home_win: number; draw: number; away_win: number };
  poisson?: PoissonData;
  cornersCards?: CornerCardsData;
  homeTeam: string;
  awayTeam: string;
}

/*
 * Mejores patas para la combinada sugerida:
 * - 1er pase: la más probable de cada categoría (Resultado, Goles, Córners,
 *   Tarjetas, Faltas) para reducir correlación.
 * - 2do pase: si faltan patas para llegar a N, rellena con las siguientes más
 *   probables (aunque repita categoría).
 * - prob entre 55% y 93%; el hándicap se excluye por solaparse con el 1X2.
 */
function pickLegs(rows: MarketRow[], n: number): MarketRow[] {
  const eligible = rows
    .filter((r) => r.category !== "Hándicap" && r.prob >= 55 && r.prob <= 93)
    .sort((a, b) => b.prob - a.prob);

  const legs: MarketRow[] = [];
  const seen = new Set<string>();
  for (const r of eligible) {
    if (legs.length >= n) break;
    if (seen.has(r.category)) continue;
    seen.add(r.category);
    legs.push(r);
  }
  if (legs.length < n) {
    for (const r of eligible) {
      if (legs.length >= n) break;
      if (legs.some((l) => l.market === r.market)) continue;
      legs.push(r);
    }
  }
  return legs.sort((a, b) => b.prob - a.prob);
}

function combinedProb(legs: MarketRow[]): number {
  return legs.reduce((acc, l) => acc * (l.prob / 100), 1) * 100;
}

function feasibility(prob: number): { label: string; color: string } {
  if (prob >= 60) return { label: "Sólida",          color: "text-emerald-400" };
  if (prob >= 40) return { label: "Moderada",        color: "text-amber-400" };
  if (prob >= 20) return { label: "Arriesgada",      color: "text-orange-400" };
  return                  { label: "Muy arriesgada", color: "text-rose-400" };
}

/* ── Fila de una pata dentro de una combinada ──────────────────────────── */
function LegRow({ leg }: { leg: MarketRow }) {
  return (
    <div className="bg-black/20 rounded-lg px-2.5 py-2 flex items-center gap-2">
      <span className={cn("text-[9px] font-bold px-1.5 py-0.5 rounded uppercase flex-shrink-0", CATEGORY_COLORS[leg.category])}>
        {leg.category.slice(0, 4)}
      </span>
      <span className="text-gray-300 text-xs flex-1 min-w-0 truncate">{leg.market}</span>
      <span className="text-white text-xs font-bold flex-shrink-0">{leg.prob.toFixed(0)}%</span>
    </div>
  );
}

/* ── Resumen prob. + cuota mínima ──────────────────────────────────────── */
function ParlaySummary({ prob }: { prob: number }) {
  const f = feasibility(prob);
  return (
    <div className="border-t border-white/10 pt-2.5 flex items-end justify-between">
      <div>
        <p className={cn("text-xl font-black leading-none", f.color)}>{prob.toFixed(1)}%</p>
        <p className="text-gray-600 text-[10px] mt-1">prob. de ganarla · {f.label}</p>
      </div>
      <div className="text-right">
        <p className="text-white text-xl font-black leading-none">&gt; {minOdds(prob).toFixed(2)}</p>
        <p className="text-gray-600 text-[10px] mt-1">cuota total mín.</p>
      </div>
    </div>
  );
}

export default function ParlaySuggestions({ probabilities, poisson, cornersCards, homeTeam, awayTeam }: Props) {
  const allRows = useMemo(
    () => buildMarketRows(probabilities, poisson, cornersCards, homeTeam, awayTeam),
    [probabilities, poisson, cornersCards, homeTeam, awayTeam]
  );
  // Pool del constructor manual: todos los mercados + marcadores exactos
  const pool = useMemo(
    () => [...allRows, ...topExactScores(poisson, homeTeam, awayTeam, 3)].sort((a, b) => b.prob - a.prob),
    [allRows, poisson, homeTeam, awayTeam]
  );

  // Máximo de patas que la sugerencia puede generar con sentido
  const maxLegs = Math.min(
    6,
    allRows.filter((r) => r.category !== "Hándicap" && r.prob >= 55 && r.prob <= 93).length
  );

  const [legCount, setLegCount] = useState(3);
  const [picked, setPicked] = useState<Set<string>>(new Set());

  if (maxLegs < 2) return null;

  const effectiveCount = Math.min(legCount, maxLegs);
  const suggested = pickLegs(allRows, effectiveCount);
  const suggestedProb = combinedProb(suggested);

  const customLegs = pool.filter((r) => picked.has(r.market));
  const customProb = customLegs.length ? combinedProb(customLegs) : 0;

  const toggle = (market: string) =>
    setPicked((prev) => {
      const next = new Set(prev);
      next.has(market) ? next.delete(market) : next.add(market);
      return next;
    });

  return (
    <div className="bg-white/5 border border-white/10 rounded-3xl p-4 sm:p-6 space-y-6">
      {/* ══ Combinada sugerida ══ */}
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-emerald-400" />
          <h3 className="text-base font-bold text-white">Combinada sugerida</h3>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-gray-400 text-xs">Número de patas:</span>
          {Array.from({ length: maxLegs - 1 }, (_, i) => i + 2).map((n) => (
            <button
              key={n}
              onClick={() => setLegCount(n)}
              className={cn(
                "w-8 h-8 rounded-lg text-sm font-bold transition-colors",
                effectiveCount === n
                  ? "bg-emerald-500 text-gray-950"
                  : "bg-white/5 text-gray-300 hover:bg-white/10 border border-white/10"
              )}
            >
              {n}
            </button>
          ))}
        </div>

        <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-4 space-y-3">
          <div className="space-y-1.5">
            {suggested.map((leg) => <LegRow key={leg.market} leg={leg} />)}
          </div>
          <ParlaySummary prob={suggestedProb} />
        </div>
        <p className="text-gray-500 text-[11px] leading-relaxed">
          Toma la selección más probable de cada categoría. A más patas, más cuota
          pero menos probabilidad de ganar — la combinada se pierde entera si falla una.
        </p>
      </div>

      {/* ══ Arma tu propia combinada ══ */}
      <div className="space-y-3 border-t border-white/10 pt-5">
        <div className="flex items-center gap-2">
          <Wand2 className="w-4 h-4 text-cyan-400" />
          <h3 className="text-base font-bold text-white">Arma tu propia combinada</h3>
        </div>
        <p className="text-gray-500 text-xs leading-relaxed">
          Marca los mercados que quieres y mira al instante qué tan factible es la combinada.
        </p>

        {/* Lista de mercados seleccionables */}
        <div className="max-h-72 overflow-y-auto rounded-2xl border border-white/10 divide-y divide-white/5">
          {pool.map((r) => {
            const on = picked.has(r.market);
            return (
              <button
                key={r.market}
                onClick={() => toggle(r.market)}
                className={cn(
                  "w-full flex items-center gap-2.5 px-3 py-2.5 text-left transition-colors",
                  on ? "bg-cyan-500/10" : "hover:bg-white/5"
                )}
              >
                <span className={cn(
                  "w-5 h-5 rounded-md flex items-center justify-center flex-shrink-0 border",
                  on ? "bg-cyan-500 border-cyan-500" : "border-white/20"
                )}>
                  {on ? <Check className="w-3.5 h-3.5 text-gray-950" /> : <Plus className="w-3 h-3 text-white/40" />}
                </span>
                <span className={cn("text-[9px] font-bold px-1.5 py-0.5 rounded uppercase flex-shrink-0", CATEGORY_COLORS[r.category])}>
                  {r.category.slice(0, 4)}
                </span>
                <span className="text-gray-300 text-xs flex-1 min-w-0 truncate">{r.market}</span>
                <span className="text-white/70 text-xs flex-shrink-0">{r.prob.toFixed(0)}%</span>
                <span className="text-gray-600 text-[10px] w-12 text-right flex-shrink-0">&gt;{minOdds(r.prob).toFixed(2)}</span>
              </button>
            );
          })}
        </div>

        {/* Resumen de la combinada armada */}
        {customLegs.length === 0 ? (
          <p className="text-gray-600 text-xs text-center py-2">
            Selecciona al menos 2 mercados para ver la factibilidad.
          </p>
        ) : (
          <div className="rounded-2xl border border-cyan-500/20 bg-cyan-500/5 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-white text-sm font-bold">
                Tu combinada · {customLegs.length} {customLegs.length === 1 ? "pata" : "patas"}
              </span>
              <button
                onClick={() => setPicked(new Set())}
                className="text-gray-500 hover:text-white text-xs transition-colors"
              >
                Limpiar
              </button>
            </div>
            <div className="space-y-1.5">
              {customLegs.map((leg) => <LegRow key={leg.market} leg={leg} />)}
            </div>
            {customLegs.length >= 2 ? (
              <ParlaySummary prob={customProb} />
            ) : (
              <p className="text-gray-500 text-xs">Agrega una pata más para formar una combinada.</p>
            )}
          </div>
        )}
      </div>

      <p className="text-gray-600 text-[11px] leading-relaxed">
        La cuota total de la combinada en Betplay debe superar la cuota mínima para que
        tenga valor. Las selecciones de un mismo partido están correlacionadas (Betplay las
        agrupa en &quot;Crea tu apuesta&quot; con cuota ajustada), así que la probabilidad
        combinada real puede diferir de la multiplicación simple. Para combinadas más
        independientes, mezcla selecciones de <span className="text-gray-400">partidos distintos</span>.
      </p>
    </div>
  );
}
