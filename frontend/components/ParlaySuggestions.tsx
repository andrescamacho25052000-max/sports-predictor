"use client";

import { Layers, AlertTriangle, ShieldCheck } from "lucide-react";
import { PoissonData, CornerCardsData } from "@/lib/api";
import { buildMarketRows, minOdds, CATEGORY_COLORS, MarketRow } from "@/lib/markets";
import { cn } from "@/lib/utils";

interface Props {
  probabilities: { home_win: number; draw: number; away_win: number };
  poisson?: PoissonData;
  cornersCards?: CornerCardsData;
  homeTeam: string;
  awayTeam: string;
}

/*
 * Selecciona las mejores patas para combinadas:
 * - máximo una por categoría (Resultado, Goles, Córners, Tarjetas, Faltas)
 *   para reducir la correlación entre selecciones del mismo partido
 * - prob entre 60% y 92%: por debajo arriesga demasiado la combinada,
 *   por encima la cuota es tan corta que no aporta casi nada al pago
 */
function pickLegs(rows: MarketRow[]): MarketRow[] {
  const eligible = rows
    // El hándicap se solapa con el resultado 1X2: lo dejamos solo en el panel
    // de valor, no como pata de combinada para no correlacionar selecciones.
    .filter((r) => r.category !== "Hándicap" && r.prob >= 60 && r.prob <= 92)
    .sort((a, b) => b.prob - a.prob);

  const seen = new Set<string>();
  const legs: MarketRow[] = [];
  for (const r of eligible) {
    if (seen.has(r.category)) continue;
    seen.add(r.category);
    legs.push(r);
  }
  return legs;
}

function combined(legs: MarketRow[]): number {
  return legs.reduce((acc, l) => acc * (l.prob / 100), 1) * 100;
}

const PRESETS = [
  {
    size: 2,
    name: "Doble conservadora",
    desc: "Las 2 selecciones más seguras de categorías distintas",
    icon: ShieldCheck,
    accent: "border-emerald-500/30 bg-emerald-500/5",
  },
  {
    size: 3,
    name: "Triple equilibrada",
    desc: "Mejor balance entre probabilidad y pago",
    icon: Layers,
    accent: "border-amber-500/25 bg-white/5",
  },
  {
    size: 4,
    name: "Cuádruple arriesgada",
    desc: "Pago alto, pero basta un fallo para perderlo todo",
    icon: AlertTriangle,
    accent: "border-rose-500/25 bg-white/5",
  },
] as const;

export default function ParlaySuggestions({ probabilities, poisson, cornersCards, homeTeam, awayTeam }: Props) {
  const legs = pickLegs(
    buildMarketRows(probabilities, poisson, cornersCards, homeTeam, awayTeam)
  );

  if (legs.length < 2) return null;

  return (
    <div className="bg-white/5 border border-white/10 rounded-3xl p-4 sm:p-6 space-y-4">
      <div className="flex items-center gap-2">
        <Layers className="w-4 h-4 text-emerald-400" />
        <h3 className="text-base font-bold text-white">Combinadas sugeridas</h3>
      </div>

      <p className="text-gray-500 text-xs leading-relaxed">
        Una por categoría (goles, córners, tarjetas…) para reducir la correlación.
        Recuerda: en una combinada <span className="text-gray-300 font-semibold">si falla
        una sola selección se pierde todo</span> — la probabilidad combinada cae rápido
        aunque cada pata sea segura.
      </p>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        {PRESETS.map((preset) => {
          if (legs.length < preset.size) return null;
          const picked  = legs.slice(0, preset.size);
          const prob    = combined(picked);
          const odds    = minOdds(prob);
          const Icon    = preset.icon;

          return (
            <div key={preset.name} className={cn("rounded-2xl border p-4 space-y-3 flex flex-col", preset.accent)}>
              <div className="flex items-start gap-2">
                <Icon className="w-4 h-4 text-gray-300 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-white font-bold text-sm">{preset.name}</p>
                  <p className="text-gray-500 text-[11px] leading-tight mt-0.5">{preset.desc}</p>
                </div>
              </div>

              <div className="space-y-1.5 flex-1">
                {picked.map((leg) => (
                  <div key={leg.market} className="bg-black/20 rounded-lg px-2.5 py-2 flex items-center gap-2">
                    <span className={cn(
                      "text-[9px] font-bold px-1.5 py-0.5 rounded uppercase flex-shrink-0",
                      CATEGORY_COLORS[leg.category]
                    )}>
                      {leg.category.slice(0, 4)}
                    </span>
                    <span className="text-gray-300 text-xs flex-1 min-w-0 truncate">{leg.market}</span>
                    <span className="text-white text-xs font-bold flex-shrink-0">{leg.prob.toFixed(0)}%</span>
                  </div>
                ))}
              </div>

              <div className="border-t border-white/10 pt-2.5 flex items-end justify-between">
                <div>
                  <p className={cn(
                    "text-xl font-black leading-none",
                    prob >= 60 ? "text-emerald-400" : prob >= 45 ? "text-amber-400" : "text-rose-400"
                  )}>
                    {prob.toFixed(1)}%
                  </p>
                  <p className="text-gray-600 text-[10px] mt-1">prob. de ganarla</p>
                </div>
                <div className="text-right">
                  <p className="text-white text-xl font-black leading-none">&gt; {odds.toFixed(2)}</p>
                  <p className="text-gray-600 text-[10px] mt-1">cuota total mín.</p>
                </div>
              </div>
            </div>
          );
        })}
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
