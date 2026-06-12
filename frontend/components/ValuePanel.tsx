"use client";

import { Target, Info } from "lucide-react";
import { PoissonData, CornerCardsData } from "@/lib/api";
import { buildMarketRows, topExactScores, minOdds, CATEGORY_COLORS } from "@/lib/markets";
import { cn } from "@/lib/utils";

interface Props {
  probabilities: { home_win: number; draw: number; away_win: number };
  poisson?: PoissonData;
  cornersCards?: CornerCardsData;
  homeTeam: string;
  awayTeam: string;
}

export default function ValuePanel({ probabilities, poisson, cornersCards, homeTeam, awayTeam }: Props) {
  const MIN_PROB = 55;   // por debajo de esto el mercado es moneda al aire
  const MAX_PROB = 93;   // por encima la cuota es tan baja que rara vez hay valor
  const MAX_ROWS = 12;

  const ranked = buildMarketRows(probabilities, poisson, cornersCards, homeTeam, awayTeam)
    .filter((r) => r.prob >= MIN_PROB && r.prob <= MAX_PROB)
    .sort((a, b) => b.prob - a.prob)
    .slice(0, MAX_ROWS);

  const scores = topExactScores(poisson, homeTeam, awayTeam, 3);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Target className="w-4 h-4 text-emerald-400" />
        <h3 className="text-base font-bold text-white">Mercados con respaldo del modelo</h3>
      </div>

      <p className="text-gray-500 text-xs leading-relaxed flex items-start gap-1.5">
        <Info className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
        Una apuesta tiene valor matemático solo si la cuota que paga Betplay es{" "}
        <span className="text-gray-300 font-semibold">mayor</span> a la cuota mínima.
        Ordenado por confianza del modelo.
      </p>

      {ranked.length === 0 ? (
        <div className="bg-white/5 border border-white/10 rounded-xl p-5 text-center">
          <p className="text-gray-400 text-sm">
            Partido muy parejo — ningún mercado supera el {MIN_PROB}% de probabilidad.
            Mejor buscar valor en otro partido.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {ranked.map((row) => {
            const odds   = minOdds(row.prob);
            const high   = row.prob >= 70;
            const medium = row.prob >= 62 && !high;

            return (
              <div
                key={row.market}
                className={cn(
                  "rounded-xl p-3.5 border flex items-center gap-3",
                  high   ? "bg-emerald-500/5 border-emerald-500/25" :
                  medium ? "bg-white/5       border-amber-500/20"   :
                           "bg-white/5       border-white/10"
                )}
              >
                <span className={cn(
                  "text-[10px] font-bold px-2 py-0.5 rounded-full flex-shrink-0 uppercase tracking-wide",
                  CATEGORY_COLORS[row.category]
                )}>
                  {row.category}
                </span>

                <span className="text-white text-sm font-medium flex-1 min-w-0 truncate">
                  {row.market}
                </span>

                <div className="flex items-center gap-4 flex-shrink-0 text-right">
                  <div>
                    <p className={cn(
                      "text-sm font-bold leading-none",
                      high ? "text-emerald-400" : medium ? "text-amber-400" : "text-gray-300"
                    )}>
                      {row.prob.toFixed(1)}%
                    </p>
                    <p className="text-gray-600 text-[10px] mt-0.5">probabilidad</p>
                  </div>
                  <div className="w-16">
                    <p className="text-white text-sm font-bold leading-none">
                      &gt; {odds.toFixed(2)}
                    </p>
                    <p className="text-gray-600 text-[10px] mt-0.5">cuota mín.</p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {scores.length > 0 && (
        <div className="space-y-2 pt-1">
          <p className="text-gray-500 text-xs font-medium uppercase tracking-wide">
            Marcador exacto — probabilidad baja, cuota alta
          </p>
          {scores.map((row) => (
            <div
              key={row.market}
              className="rounded-xl p-3.5 border border-white/10 bg-white/5 flex items-center gap-3"
            >
              <span className={cn(
                "text-[10px] font-bold px-2 py-0.5 rounded-full flex-shrink-0 uppercase tracking-wide",
                CATEGORY_COLORS[row.category]
              )}>
                {row.category}
              </span>

              <span className="text-white text-sm font-medium flex-1 min-w-0 truncate">
                {row.market}
              </span>

              <div className="flex items-center gap-4 flex-shrink-0 text-right">
                <div>
                  <p className="text-sm font-bold leading-none text-gray-300">{row.prob.toFixed(1)}%</p>
                  <p className="text-gray-600 text-[10px] mt-0.5">probabilidad</p>
                </div>
                <div className="w-16">
                  <p className="text-white text-sm font-bold leading-none">
                    &gt; {minOdds(row.prob).toFixed(2)}
                  </p>
                  <p className="text-gray-600 text-[10px] mt-0.5">cuota mín.</p>
                </div>
              </div>
            </div>
          ))}
          <p className="text-gray-600 text-[11px] leading-relaxed">
            El marcador exacto falla la mayoría de las veces incluso cuando el modelo acierta
            la tendencia — úsalo con montos pequeños y nunca como pata de una combinada.
          </p>
        </div>
      )}

      <p className="text-gray-600 text-[11px] leading-relaxed">
        Probabilidades estimadas por el modelo, no garantías. Cuota mínima = 100 / probabilidad:
        si Betplay paga menos, la apuesta tiene valor esperado negativo aunque sea probable que gane.
      </p>
    </div>
  );
}
