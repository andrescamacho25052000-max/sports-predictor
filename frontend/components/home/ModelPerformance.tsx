"use client";

import { useEffect, useState } from "react";
import { LineChart } from "lucide-react";
import { fetchMarketStats, fetchStats, MarketStats, GlobalStats } from "@/lib/api";

interface Row {
  label: string;
  n: number;
  acc: number | null;
}

function Bar({ row }: { row: Row }) {
  // El backend ya devuelve la precisión como porcentaje (0-100).
  const pct = row.acc != null ? Math.round(row.acc) : null;
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="text-white/80">{row.label}</span>
        <span className="font-mono text-muted-2">
          {pct != null ? (
            <>
              <span className="text-accent font-semibold">{pct}%</span> ·{" "}
              {row.n} ev.
            </>
          ) : (
            "sin datos"
          )}
        </span>
      </div>
      <div className="h-2 rounded-full bg-white/[0.05] overflow-hidden">
        {pct != null && (
          <div
            className="h-full rounded-full bg-gradient-to-r from-accent to-accent-2"
            style={{ width: `${Math.max(3, Math.min(100, pct))}%` }}
          />
        )}
      </div>
    </div>
  );
}

/**
 * Módulo "Rendimiento del modelo" (estilo Statix). Precisión real por mercado
 * desde el backend — medición honesta, no cifras infladas (doc. 18.5).
 */
export default function ModelPerformance() {
  const [market, setMarket] = useState<MarketStats | null>(null);
  const [global, setGlobal] = useState<GlobalStats | null>(null);

  useEffect(() => {
    let alive = true;
    Promise.allSettled([fetchMarketStats(), fetchStats()]).then(
      ([m, g]) => {
        if (!alive) return;
        if (m.status === "fulfilled") setMarket(m.value);
        if (g.status === "fulfilled") setGlobal(g.value);
      }
    );
    return () => {
      alive = false;
    };
  }, []);

  const rows: Row[] = market
    ? [
        { label: "Ganador (1X2)", n: market.result_1x2.n, acc: market.result_1x2.accuracy },
        { label: "Más / Menos 2.5", n: market.over_under_25.n, acc: market.over_under_25.accuracy },
        { label: "Ambos marcan", n: market.btts.n, acc: market.btts.accuracy },
      ]
    : [];

  return (
    <section className="rounded-3xl border border-border bg-surface p-5 sm:p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <p className="eyebrow">Rendimiento del modelo</p>
          <h2 className="text-lg font-bold text-white mt-1">
            Precisión real por mercado
          </h2>
          <p className="text-xs text-muted-2 mt-0.5">
            Medición honesta sobre resultados ya jugados
          </p>
        </div>
        <span className="grid place-items-center h-9 w-9 rounded-xl bg-accent/15 text-accent">
          <LineChart size={18} />
        </span>
      </div>

      {global?.accuracy != null && (
        <div className="rounded-2xl border border-border bg-surface-2 px-4 py-3 flex items-baseline gap-2">
          <span className="font-mono text-2xl font-bold text-accent">
            {global.accuracy.toFixed(1)}%
          </span>
          <span className="text-xs text-muted-2">
            acierto global 1X2 sobre {global.evaluated} partidos evaluados
          </span>
        </div>
      )}

      <div className="space-y-4">
        {market ? (
          rows.map((r) => <Bar key={r.label} row={r} />)
        ) : (
          Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-8 rounded-lg bg-white/[0.04] animate-pulse" />
          ))
        )}
      </div>

      <p className="text-[11px] text-muted-2 leading-relaxed border-t border-border pt-3">
        El valor esperado (EV) se muestra como información, no como ganancia
        asegurada: en ligas grandes el modelo no supera al mercado.
      </p>
    </section>
  );
}
