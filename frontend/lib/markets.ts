import { PoissonData, CornerCardsData } from "@/lib/api";

/*
 * Construcción centralizada de mercados apostables con su probabilidad.
 * Usado por ValuePanel (lista plana) y ParlaySuggestions (combinadas).
 */

export type MarketCategory =
  | "Resultado" | "Goles" | "Córners" | "Tarjetas" | "Faltas" | "Marcador" | "Hándicap";

export interface MarketRow {
  market: string;
  category: MarketCategory;
  prob: number; // 0-100
}

export const CATEGORY_COLORS: Record<MarketCategory, string> = {
  Resultado: "bg-emerald-500/15 text-emerald-400",
  Goles:     "bg-sky-500/15     text-sky-400",
  Córners:   "bg-amber-500/15   text-amber-400",
  Tarjetas:  "bg-rose-500/15    text-rose-400",
  Faltas:    "bg-violet-500/15  text-violet-400",
  Marcador:  "bg-fuchsia-500/15 text-fuchsia-400",
  Hándicap:  "bg-cyan-500/15    text-cyan-400",
};

/**
 * Top N marcadores exactos como mercados (cuota alta, probabilidad baja).
 * Van aparte de buildMarketRows para que no entren al filtro de seguridad
 * del panel ni a las combinadas.
 */
export function topExactScores(
  poisson: PoissonData | undefined,
  homeTeam: string,
  awayTeam: string,
  n = 3,
): MarketRow[] {
  if (!poisson?.exact_score?.length) return [];
  return poisson.exact_score.slice(0, n).map((s) => ({
    market: `Marcador exacto ${s.score} (${homeTeam} ${s.home}-${s.away} ${awayTeam})`,
    category: "Marcador" as const,
    prob: s.prob,
  }));
}

/** Cuota mínima para que la apuesta tenga valor: 100 / probabilidad. */
export function minOdds(prob: number): number {
  return 100 / prob;
}

/** P(X > línea) para una Poisson con media lambda (línea tipo 25.5). Devuelve 0-100. */
export function poissonOver(lambda: number, line: number): number {
  let cdf = 0;
  let term = Math.exp(-lambda); // P(X=0)
  const k = Math.floor(line);
  for (let i = 0; i <= k; i++) {
    if (i > 0) term *= lambda / i;
    cdf += term;
  }
  return (1 - cdf) * 100;
}

export function buildMarketRows(
  probabilities: { home_win: number; draw: number; away_win: number },
  poisson: PoissonData | undefined,
  cornersCards: CornerCardsData | undefined,
  homeTeam: string,
  awayTeam: string,
): MarketRow[] {
  const rows: MarketRow[] = [];
  const { home_win, draw, away_win } = probabilities;

  // ── Resultado (XGBoost) + dobles oportunidades ─────────────────────────
  rows.push(
    { market: `Gana ${homeTeam} (1)`,           category: "Resultado", prob: home_win },
    { market: "Empate (X)",                      category: "Resultado", prob: draw },
    { market: `Gana ${awayTeam} (2)`,            category: "Resultado", prob: away_win },
    { market: `${homeTeam} o empate (1X)`,       category: "Resultado", prob: home_win + draw },
    { market: `${awayTeam} o empate (X2)`,       category: "Resultado", prob: draw + away_win },
    { market: `${homeTeam} o ${awayTeam} (12)`,  category: "Resultado", prob: home_win + away_win },
  );

  if (poisson) {
    // ── Goles totales ────────────────────────────────────────────────────
    const ou = poisson.over_under;
    for (const line of ["0.5", "1.5", "2.5", "3.5", "4.5"]) {
      const over  = ou[`over_${line}`];
      const under = ou[`under_${line}`];
      if (over  != null) rows.push({ market: `Más de ${line} goles`,   category: "Goles", prob: over });
      if (under != null) rows.push({ market: `Menos de ${line} goles`, category: "Goles", prob: under });
    }
    rows.push(
      { market: "Ambos equipos marcan: Sí", category: "Goles", prob: poisson.btts.yes },
      { market: "Ambos equipos marcan: No", category: "Goles", prob: poisson.btts.no },
    );

    // ── Goles por equipo ─────────────────────────────────────────────────
    const hg = poisson.home_goals;
    const ag = poisson.away_goals;
    if (hg?.home_over_0_5 != null)
      rows.push({ market: `${homeTeam} marca al menos 1 gol`, category: "Goles", prob: hg.home_over_0_5 });
    if (ag?.away_over_0_5 != null)
      rows.push({ market: `${awayTeam} marca al menos 1 gol`, category: "Goles", prob: ag.away_over_0_5 });
    if (hg?.home_under_1_5 != null)
      rows.push({ market: `${homeTeam} marca máximo 1 gol`, category: "Goles", prob: hg.home_under_1_5 });
    if (ag?.away_under_1_5 != null)
      rows.push({ market: `${awayTeam} marca máximo 1 gol`, category: "Goles", prob: ag.away_under_1_5 });

    // ── Primer tiempo ────────────────────────────────────────────────────
    const ht = poisson.half_time;
    rows.push(
      { market: `Empate al descanso`,                category: "Resultado", prob: ht.draw },
      { market: `${homeTeam} o empate al descanso`,  category: "Resultado", prob: ht.home_win + ht.draw },
    );

    // ── Hándicap asiático (derivado de la matriz de marcadores) ──────────
    const hc = poisson.handicap;
    if (hc) {
      const hcDefs: [string, string][] = [
        ["home_-1.5", `${homeTeam} −1.5 (gana por 2+)`],
        ["home_-2.5", `${homeTeam} −2.5 (gana por 3+)`],
        ["home_+1.5", `${homeTeam} +1.5 (no pierde por 2+)`],
        ["home_+2.5", `${homeTeam} +2.5 (no pierde por 3+)`],
        ["away_-1.5", `${awayTeam} −1.5 (gana por 2+)`],
        ["away_-2.5", `${awayTeam} −2.5 (gana por 3+)`],
        ["away_+1.5", `${awayTeam} +1.5 (no pierde por 2+)`],
        ["away_+2.5", `${awayTeam} +2.5 (no pierde por 3+)`],
      ];
      for (const [key, label] of hcDefs) {
        if (hc[key] != null) rows.push({ market: label, category: "Hándicap", prob: hc[key] });
      }
    }
  }

  if (cornersCards) {
    // corners/tarjetas vienen como fracción 0-1 (no porcentaje)
    const co = cornersCards.corners.over_under;
    for (const line of Object.keys(co)) {
      const v = co[line];
      if (v != null) {
        rows.push(
          { market: `Más de ${line} córners`,   category: "Córners", prob: v * 100 },
          { market: `Menos de ${line} córners`, category: "Córners", prob: (1 - v) * 100 },
        );
      }
    }

    const yc = cornersCards.yellow_cards.over_under;
    for (const line of Object.keys(yc)) {
      const v = yc[line];
      if (v != null) {
        rows.push(
          { market: `Más de ${line} amarillas`,   category: "Tarjetas", prob: v * 100 },
          { market: `Menos de ${line} amarillas`, category: "Tarjetas", prob: (1 - v) * 100 },
        );
      }
    }

    // ── Faltas: el backend da el promedio; las líneas se derivan con Poisson ──
    const lambda = cornersCards.fouls.expected_total;
    if (lambda > 0) {
      const base = Math.round(lambda);
      for (const offset of [-4.5, -2.5, -0.5, 1.5, 3.5]) {
        const line = base + offset;
        if (line < 10) continue;
        const over = poissonOver(lambda, line);
        rows.push(
          { market: `Más de ${line} faltas`,   category: "Faltas", prob: over },
          { market: `Menos de ${line} faltas`, category: "Faltas", prob: 100 - over },
        );
      }
    }
  }

  return rows;
}
