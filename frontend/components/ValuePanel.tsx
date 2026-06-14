"use client";

import { Target, Info } from "lucide-react";
import { PoissonData, CornerCardsData } from "@/lib/api";
import { buildMarketRows, topExactScores, minOdds, CATEGORY_COLORS, MarketRow, MarketCategory } from "@/lib/markets";
import { cn } from "@/lib/utils";

interface Props {
  probabilities: { home_win: number; draw: number; away_win: number };
  poisson?: PoissonData;
  cornersCards?: CornerCardsData;
  homeTeam: string;
  awayTeam: string;
}

// Orden en que se muestran las secciones de mercados
const CATEGORY_ORDER: MarketCategory[] = [
  "Resultado", "Hándicap", "Goles", "Córners", "Tarjetas", "Faltas",
];

const MAX_PER_CATEGORY = 6;

function MarketRowItem({ row, plain = false }: { row: MarketRow; plain?: boolean }) {
  const high   = row.prob >= 70;
  const medium = row.prob >= 62 && !high;
  return (
    <div
      className={cn(
        "rounded-xl p-3.5 border flex items-center gap-3",
        plain  ? "bg-white/5 border-white/10" :
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

      <span className="text-white text-sm font-medium flex-1 min-w-0 truncate">{row.market}</span>

      <div className="flex items-center gap-4 flex-shrink-0 text-right">
        <div>
          <p className={cn(
            "text-sm font-bold leading-none",
            plain ? "text-gray-300" : high ? "text-emerald-400" : medium ? "text-amber-400" : "text-gray-300"
          )}>
            {row.prob.toFixed(1)}%
          </p>
          <p className="text-gray-600 text-[10px] mt-0.5">probabilidad</p>
        </div>
        <div className="w-16">
          <p className="text-white text-sm font-bold leading-none">&gt; {minOdds(row.prob).toFixed(2)}</p>
          <p className="text-gray-600 text-[10px] mt-0.5">cuota mín.</p>
        </div>
      </div>
    </div>
  );
}

export default function ValuePanel({ probabilities, poisson, cornersCards, homeTeam, awayTeam }: Props) {
  const MIN_PROB = 55;   // por debajo de esto el mercado es moneda al aire
  const MAX_PROB = 93;   // por encima la cuota es tan baja que rara vez hay valor

  const eligible = buildMarketRows(probabilities, poisson, cornersCards, homeTeam, awayTeam)
    .filter((r) => r.prob >= MIN_PROB && r.prob <= MAX_PROB);

  // Agrupar por categoría y ordenar cada grupo por probabilidad
  const byCategory: Record<string, MarketRow[]> = {};
  for (const r of eligible) {
    (byCategory[r.category] ??= []).push(r);
  }
  for (const c of Object.keys(byCategory)) {
    byCategory[c].sort((a, b) => b.prob - a.prob);
  }

  const sections = CATEGORY_ORDER
    .filter((c) => byCategory[c]?.length)
    .map((c) => ({ category: c, rows: byCategory[c].slice(0, MAX_PER_CATEGORY) }));

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
        Agrupado por mercado; dentro de cada uno, ordenado por confianza.
      </p>

      {sections.length === 0 ? (
        <div className="bg-white/5 border border-white/10 rounded-xl p-5 text-center">
          <p className="text-gray-400 text-sm">
            Partido muy parejo — ningún mercado supera el {MIN_PROB}% de probabilidad.
            Mejor buscar valor en otro partido.
          </p>
        </div>
      ) : (
        <div className="space-y-5">
          {sections.map(({ category, rows }) => (
            <div key={category} className="space-y-2">
              <div className="flex items-center gap-2">
                <span className={cn(
                  "text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wide",
                  CATEGORY_COLORS[category]
                )}>
                  {category}
                </span>
                <div className="flex-1 h-px bg-white/10" />
              </div>
              {rows.map((row) => <MarketRowItem key={row.market} row={row} />)}
            </div>
          ))}
        </div>
      )}

      {scores.length > 0 && (
        <div className="space-y-2 pt-1">
          <div className="flex items-center gap-2">
            <span className={cn(
              "text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wide",
              CATEGORY_COLORS["Marcador"]
            )}>
              Marcador
            </span>
            <span className="text-gray-500 text-xs">— probabilidad baja, cuota alta</span>
            <div className="flex-1 h-px bg-white/10" />
          </div>
          {scores.map((row) => <MarketRowItem key={row.market} row={row} plain />)}
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
