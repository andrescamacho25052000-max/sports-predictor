"use client";

import { Target, Info } from "lucide-react";
import { PoissonData, CornerCardsData } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Props {
  probabilities: { home_win: number; draw: number; away_win: number };
  poisson?: PoissonData;
  cornersCards?: CornerCardsData;
  homeTeam: string;
  awayTeam: string;
}

interface MarketRow {
  market: string;
  category: "Resultado" | "Goles" | "Córners" | "Tarjetas";
  prob: number; // 0-100
}

const CATEGORY_COLORS: Record<MarketRow["category"], string> = {
  Resultado: "bg-emerald-500/15 text-emerald-400",
  Goles:     "bg-sky-500/15     text-sky-400",
  Córners:   "bg-amber-500/15   text-amber-400",
  Tarjetas:  "bg-rose-500/15    text-rose-400",
};

function buildRows(
  probabilities: Props["probabilities"],
  poisson: PoissonData | undefined,
  cornersCards: CornerCardsData | undefined,
  homeTeam: string,
  awayTeam: string,
): MarketRow[] {
  const rows: MarketRow[] = [];
  const { home_win, draw, away_win } = probabilities;

  rows.push(
    { market: `Gana ${homeTeam} (1)`,           category: "Resultado", prob: home_win },
    { market: "Empate (X)",                      category: "Resultado", prob: draw },
    { market: `Gana ${awayTeam} (2)`,            category: "Resultado", prob: away_win },
    { market: `${homeTeam} o empate (1X)`,       category: "Resultado", prob: home_win + draw },
    { market: `${awayTeam} o empate (X2)`,       category: "Resultado", prob: draw + away_win },
    { market: `${homeTeam} o ${awayTeam} (12)`,  category: "Resultado", prob: home_win + away_win },
  );

  if (poisson) {
    const ou = poisson.over_under;
    for (const line of ["1.5", "2.5", "3.5"]) {
      const over  = ou[`over_${line}`];
      const under = ou[`under_${line}`];
      if (over  != null) rows.push({ market: `Más de ${line} goles`,   category: "Goles", prob: over });
      if (under != null) rows.push({ market: `Menos de ${line} goles`, category: "Goles", prob: under });
    }
    rows.push(
      { market: "Ambos equipos marcan: Sí", category: "Goles", prob: poisson.btts.yes },
      { market: "Ambos equipos marcan: No", category: "Goles", prob: poisson.btts.no },
    );
  }

  if (cornersCards) {
    // corners/tarjetas vienen como fracción 0-1 (no porcentaje)
    const co = cornersCards.corners.over_under;
    for (const line of ["7.5", "8.5", "9.5"]) {
      const v = co[line];
      if (v != null) {
        rows.push(
          { market: `Más de ${line} córners`,   category: "Córners", prob: v * 100 },
          { market: `Menos de ${line} córners`, category: "Córners", prob: (1 - v) * 100 },
        );
      }
    }
    const yc = cornersCards.yellow_cards.over_under;
    for (const line of ["2.5", "3.5", "4.5"]) {
      const v = yc[line];
      if (v != null) {
        rows.push(
          { market: `Más de ${line} amarillas`,   category: "Tarjetas", prob: v * 100 },
          { market: `Menos de ${line} amarillas`, category: "Tarjetas", prob: (1 - v) * 100 },
        );
      }
    }
  }

  return rows;
}

export default function ValuePanel({ probabilities, poisson, cornersCards, homeTeam, awayTeam }: Props) {
  const MIN_PROB = 55;   // por debajo de esto el mercado es moneda al aire
  const MAX_ROWS = 12;

  const ranked = buildRows(probabilities, poisson, cornersCards, homeTeam, awayTeam)
    .filter((r) => r.prob >= MIN_PROB)
    .sort((a, b) => b.prob - a.prob)
    .slice(0, MAX_ROWS);

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
            const minOdds = 100 / row.prob;
            const high    = row.prob >= 70;
            const medium  = row.prob >= 62 && !high;

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
                      &gt; {minOdds.toFixed(2)}
                    </p>
                    <p className="text-gray-600 text-[10px] mt-0.5">cuota mín.</p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <p className="text-gray-600 text-[11px] leading-relaxed">
        Probabilidades estimadas por el modelo, no garantías. Cuota mínima = 100 / probabilidad:
        si Betplay paga menos, la apuesta tiene valor esperado negativo aunque sea probable que gane.
      </p>
    </div>
  );
}
