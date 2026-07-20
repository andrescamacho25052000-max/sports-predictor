"use client";

import { Target, Info, Zap, TrendingUp } from "lucide-react";
import { PoissonData, CornerCardsData, OddsData, OddsMarket } from "@/lib/api";
import { buildMarketRows, topExactScores, minOdds, CATEGORY_COLORS, MarketRow, MarketCategory } from "@/lib/markets";
import { cn } from "@/lib/utils";

interface Props {
  probabilities: { home_win: number; draw: number; away_win: number };
  poisson?: PoissonData;
  cornersCards?: CornerCardsData;
  odds?: OddsData;
  homeTeam: string;
  awayTeam: string;
}

// Orden en que se muestran las secciones de mercados
const CATEGORY_ORDER: MarketCategory[] = [
  "Resultado", "Hándicap", "Goles", "Córners", "Tarjetas", "Faltas",
];

const MAX_PER_CATEGORY = 6;

/** Formatea el EV (0.08 → "+8%"). */
function fmtEv(ev: number): string {
  const pct = Math.round(ev * 100);
  return `${pct > 0 ? "+" : ""}${pct}%`;
}

/** Badge de EV: verde si hay valor, rojo si no. */
function EvBadge({ info }: { info: OddsMarket }) {
  return (
    <span
      className={cn(
        "text-[10px] font-bold px-1.5 py-0.5 rounded-md whitespace-nowrap",
        info.value ? "bg-emerald-500/20 text-emerald-300" : "bg-red-500/15 text-red-300"
      )}
      title={info.value ? "Valor esperado positivo" : "Valor esperado negativo"}
    >
      {fmtEv(info.ev)}
    </span>
  );
}

function MarketRowItem({ row, oddsInfo, plain = false }: { row: MarketRow; oddsInfo?: OddsMarket; plain?: boolean }) {
  const high   = row.prob >= 70;
  const medium = row.prob >= 62 && !high;
  const hasValue = oddsInfo?.value;
  return (
    <div
      className={cn(
        "rounded-xl p-3.5 border flex items-center gap-3",
        hasValue ? "bg-emerald-500/10 border-emerald-500/40" :
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

        {oddsInfo ? (
          // Cuota real disponible → mostramos la cuota del mercado y el EV
          <div className="w-20">
            <div className="flex items-center justify-end gap-1.5 leading-none">
              <span className="text-white text-sm font-bold">{oddsInfo.odds.toFixed(2)}</span>
              <EvBadge info={oddsInfo} />
            </div>
            <p className="text-gray-600 text-[10px] mt-0.5">cuota real · EV</p>
          </div>
        ) : (
          <div className="w-16">
            <p className="text-white text-sm font-bold leading-none">&gt; {minOdds(row.prob).toFixed(2)}</p>
            <p className="text-gray-600 text-[10px] mt-0.5">cuota mín.</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function ValuePanel({ probabilities, poisson, cornersCards, odds, homeTeam, awayTeam }: Props) {
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

  // Etiqueta legible para cada mercado de valor (clave técnica → texto)
  const valueLabel = (key: string): string => {
    if (key === "1") return `Gana ${homeTeam}`;
    if (key === "X") return "Empate";
    if (key === "2") return `Gana ${awayTeam}`;
    if (key.startsWith("over_")) return `Más de ${key.slice(5)} goles`;
    if (key.startsWith("under_")) return `Menos de ${key.slice(6)} goles`;
    return key;
  };

  const bestValue = odds?.best_value ?? [];

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Target className="w-4 h-4 text-emerald-400" />
        <h3 className="text-base font-bold text-white">Mercados con respaldo del modelo</h3>
      </div>

      {/* ── Valor real detectado (solo si hay cuotas reales) ── */}
      {odds && (
        bestValue.length > 0 ? (
          <div className="bg-gradient-to-br from-emerald-500/15 to-emerald-700/5 border border-emerald-500/30 rounded-2xl p-4">
            <div className="flex items-center gap-2 mb-3">
              <Zap className="w-4 h-4 text-emerald-400" />
              <h4 className="text-sm font-bold text-emerald-300">Valor real detectado</h4>
              <span className="text-[11px] text-emerald-400/60">
                cuotas de {odds.bookmaker_count} casa{odds.bookmaker_count !== 1 ? "s" : ""}
              </span>
            </div>
            <div className="space-y-2">
              {bestValue.map((m) => (
                <div key={m.market} className="flex items-center justify-between bg-emerald-500/10 rounded-xl px-3 py-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <TrendingUp className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                    <span className="text-white text-sm font-medium truncate">{valueLabel(m.market)}</span>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className="text-white text-sm font-bold">{m.odds.toFixed(2)}</span>
                    <EvBadge info={m} />
                  </div>
                </div>
              ))}
            </div>
            <p className="text-emerald-400/50 text-[11px] mt-3 leading-relaxed">
              EV positivo = la cuota paga más de lo que el riesgo merece según el modelo.
              A largo plazo, apostar solo donde hay valor es lo que da ganancia.
            </p>
          </div>
        ) : (
          <div className="bg-white/5 border border-white/10 rounded-xl p-4 text-center">
            <p className="text-gray-400 text-sm">
              Cuotas reales analizadas ({odds.bookmaker_count} casa{odds.bookmaker_count !== 1 ? "s" : ""}):
              ningún mercado tiene valor esperado positivo ahora mismo.
            </p>
          </div>
        )
      )}

      <p className="text-gray-500 text-xs leading-relaxed flex items-start gap-1.5">
        <Info className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
        {odds
          ? "Las cuotas reales se traen automáticamente. Una apuesta tiene valor si su EV es positivo (verde)."
          : "Una apuesta tiene valor matemático solo si la cuota que paga Betplay es mayor a la cuota mínima."}
        {" "}Agrupado por mercado; dentro de cada uno, ordenado por confianza.
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
              {rows.map((row) => (
                <MarketRowItem
                  key={row.market}
                  row={row}
                  oddsInfo={row.oddsKey ? odds?.markets[row.oddsKey] : undefined}
                />
              ))}
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
