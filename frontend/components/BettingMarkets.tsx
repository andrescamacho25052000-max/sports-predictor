"use client";

interface ExactScore { score: string; home: number; away: number; prob: number; }

interface PoissonData {
  expected_goals:   { home: number; away: number; total: number };
  result_1x2:       { home_win: number; draw: number; away_win: number };
  over_under:       Record<string, number>;
  btts:             { yes: number; no: number };
  exact_score:      ExactScore[];
  half_time:        { home_win: number; draw: number; away_win: number };
  home_goals:       Record<string, number>;
  away_goals:       Record<string, number>;
  home_clean_sheet: { yes: number; no: number };
  away_clean_sheet: { yes: number; no: number };
}

interface Props {
  poisson:  PoissonData;
  homeTeam: string;
  awayTeam: string;
}

/* ─── helpers ─────────────────────────────────────────────────────────────── */

function probColor(p: number) {
  if (p >= 65) return "text-emerald-400";
  if (p >= 45) return "text-yellow-400";
  if (p >= 25) return "text-orange-400";
  return "text-gray-500";
}

function probBg(p: number) {
  if (p >= 65) return "bg-emerald-500/15 border-emerald-500/35";
  if (p >= 45) return "bg-yellow-500/12 border-yellow-500/30";
  if (p >= 25) return "bg-orange-500/10 border-orange-500/20";
  return "bg-white/4 border-white/8";
}

function confidence(p: number) {
  if (p >= 75) return { label: "Muy probable", dot: "bg-emerald-400" };
  if (p >= 55) return { label: "Probable",     dot: "bg-yellow-400" };
  if (p >= 35) return { label: "Posible",       dot: "bg-orange-400" };
  return        { label: "Poco probable",        dot: "bg-gray-600"  };
}

/** Cuota mínima de Betplay para que la apuesta tenga valor. */
function mo(p: number) {
  if (p <= 0) return "—";
  return `> ${(100 / p).toFixed(2)}`;
}

/* ─── bloques reutilizables ──────────────────────────────────────────────── */

function SectionCard({ icon, title, subtitle, children }: {
  icon: string; title: string; subtitle?: string; children: React.ReactNode;
}) {
  return (
    <div className="bg-white/4 border border-white/8 rounded-2xl p-5 space-y-4">
      <div className="flex items-start gap-3">
        <span className="text-2xl leading-none mt-0.5">{icon}</span>
        <div>
          <p className="text-white font-bold text-sm">{title}</p>
          {subtitle && <p className="text-gray-500 text-xs mt-0.5">{subtitle}</p>}
        </div>
      </div>
      {children}
    </div>
  );
}

function BigOption({ label, prob, highlight }: { label: string; prob: number; highlight?: boolean }) {
  const conf = confidence(prob);
  return (
    <div className={`rounded-xl border p-4 text-center space-y-1.5 transition-all
      ${highlight ? probBg(prob) : "bg-white/4 border-white/8"}`}>
      <p className="text-xs text-gray-400 leading-tight">{label}</p>
      <p className={`text-2xl font-black ${probColor(prob)}`}>{prob}%</p>
      <div className="flex items-center justify-center gap-1.5">
        <span className={`w-1.5 h-1.5 rounded-full ${conf.dot}`} />
        <span className="text-xs text-gray-500">{conf.label}</span>
      </div>
      <p className="text-[10px] text-gray-600">cuota mín. {mo(prob)}</p>
    </div>
  );
}

function GoalLineRow({ question, overProb, underLabel, underProb }: {
  question: string; overProb: number; underLabel: string; underProb: number;
}) {
  const isOverFav = overProb >= underProb;
  return (
    <div className="space-y-1.5">
      <p className="text-xs text-gray-500 pl-1">{question}</p>
      <div className="grid grid-cols-2 gap-2">
        <div className={`rounded-xl border px-4 py-3 flex items-center justify-between
          ${isOverFav ? probBg(overProb) : "bg-white/4 border-white/8"}`}>
          <span className="text-sm text-gray-300">Sí</span>
          <span className="text-right">
            <span className={`text-base font-black ${probColor(overProb)}`}>{overProb}%</span>
            <span className="block text-[10px] text-gray-600">{mo(overProb)}</span>
          </span>
        </div>
        <div className={`rounded-xl border px-4 py-3 flex items-center justify-between
          ${!isOverFav ? probBg(underProb) : "bg-white/4 border-white/8"}`}>
          <span className="text-sm text-gray-300">{underLabel}</span>
          <span className="text-right">
            <span className={`text-base font-black ${probColor(underProb)}`}>{underProb}%</span>
            <span className="block text-[10px] text-gray-600">{mo(underProb)}</span>
          </span>
        </div>
      </div>
    </div>
  );
}

/* ─── componente principal ───────────────────────────────────────────────── */

export default function BettingMarkets({ poisson, homeTeam, awayTeam }: Props) {
  const { expected_goals: xg, over_under: ou, btts, exact_score,
          half_time: ht, home_goals: hg, away_goals: ag,
          home_clean_sheet: hcs, away_clean_sheet: acs } = poisson;

  const home = homeTeam.split(" ").slice(-1)[0];
  const away = awayTeam.split(" ").slice(-1)[0];
  const topScore = exact_score[0];

  return (
    <div className="space-y-4">

      {/* ── Título de sección ── */}
      <div className="flex items-center gap-3 px-1">
        <div className="flex-1 h-px bg-white/10" />
        <p className="text-xs font-bold text-gray-500 uppercase tracking-widest whitespace-nowrap">
          Mercados de apuesta
        </p>
        <div className="flex-1 h-px bg-white/10" />
      </div>

      {/* ── 1. Resumen de goles esperados ── */}
      <SectionCard
        icon="⚽"
        title="¿Cuántos goles se esperan?"
        subtitle="Basado en el promedio de ataque y defensa de cada equipo"
      >
        <div className="grid grid-cols-3 gap-2 text-center">
          <div className="bg-white/5 rounded-xl py-4 border border-white/8">
            <p className="text-xs text-gray-500 mb-1">{home}</p>
            <p className="text-3xl font-black text-blue-400">{xg.home}</p>
            <p className="text-xs text-gray-600 mt-0.5">goles</p>
          </div>
          <div className="bg-emerald-500/10 rounded-xl py-4 border border-emerald-500/20">
            <p className="text-xs text-gray-500 mb-1">Total</p>
            <p className="text-3xl font-black text-white">{xg.total}</p>
            <p className="text-xs text-gray-600 mt-0.5">goles</p>
          </div>
          <div className="bg-white/5 rounded-xl py-4 border border-white/8">
            <p className="text-xs text-gray-500 mb-1">{away}</p>
            <p className="text-3xl font-black text-purple-400">{xg.away}</p>
            <p className="text-xs text-gray-600 mt-0.5">goles</p>
          </div>
        </div>
      </SectionCard>

      {/* ── 2. Marcador más probable ── */}
      <SectionCard
        icon="🎯"
        title="Marcadores más probables"
        subtitle="Los 10 resultados exactos con mayor probabilidad"
      >
        {/* Top 1 destacado */}
        <div className={`rounded-xl border p-4 flex items-center justify-between ${probBg(topScore.prob * 3)}`}>
          <div>
            <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider">
              ★ Resultado más probable
            </span>
            <p className="text-3xl font-black text-white mt-1">{topScore.score}</p>
            <p className="text-xs text-gray-400 mt-1">
              {homeTeam} {topScore.home} — {topScore.away} {awayTeam}
            </p>
          </div>
          <div className="text-right">
            <p className={`text-3xl font-black ${probColor(topScore.prob * 3)}`}>{topScore.prob}%</p>
            <p className="text-xs text-gray-500">probabilidad</p>
          </div>
        </div>

        {/* Resto en grid */}
        <div className="grid grid-cols-3 gap-2">
          {exact_score.slice(1, 10).map((s, i) => (
            <div key={s.score}
              className={`rounded-xl border p-2.5 text-center ${i === 0 ? probBg(s.prob * 2.5) : "bg-white/4 border-white/8"}`}>
              <p className={`text-lg font-black ${i === 0 ? probColor(s.prob * 2.5) : "text-gray-300"}`}>{s.score}</p>
              <p className="text-xs text-gray-500 mt-0.5">{s.prob}%</p>
            </div>
          ))}
        </div>
      </SectionCard>

      {/* ── 3. ¿Cuántos goles en total? ── */}
      <SectionCard
        icon="📊"
        title="¿Cuántos goles habrá en el partido?"
        subtitle="Over = más goles de ese número · Under = menos goles"
      >
        <div className="space-y-3">
          {[
            { line: 0.5, pregunta: "¿Habrá al menos 1 gol?" },
            { line: 1.5, pregunta: "¿Habrá al menos 2 goles?" },
            { line: 2.5, pregunta: "¿Habrá al menos 3 goles?" },
            { line: 3.5, pregunta: "¿Habrá al menos 4 goles?" },
            { line: 4.5, pregunta: "¿Habrá al menos 5 goles?" },
          ].map(({ line, pregunta }) => {
            const over  = ou[`over_${line}`];
            const under = ou[`under_${line}`];
            const favOver = over >= under;
            return (
              <div key={line} className="space-y-1">
                <p className="text-xs text-gray-500 pl-1">{pregunta}</p>
                <div className="grid grid-cols-2 gap-2">
                  <div className={`rounded-xl border px-4 py-2.5 flex items-center justify-between
                    ${favOver ? probBg(over) : "bg-white/4 border-white/8"}`}>
                    <span className="text-sm text-gray-300">Sí (Over {line})</span>
                    <span className="text-right">
                      <span className={`text-base font-black ${probColor(over)}`}>{over}%</span>
                      <span className="block text-[10px] text-gray-600">{mo(over)}</span>
                    </span>
                  </div>
                  <div className={`rounded-xl border px-4 py-2.5 flex items-center justify-between
                    ${!favOver ? probBg(under) : "bg-white/4 border-white/8"}`}>
                    <span className="text-sm text-gray-300">No (Under {line})</span>
                    <span className="text-right">
                      <span className={`text-base font-black ${probColor(under)}`}>{under}%</span>
                      <span className="block text-[10px] text-gray-600">{mo(under)}</span>
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </SectionCard>

      {/* ── 4. ¿Marcan los dos? ── */}
      <SectionCard
        icon="🔁"
        title="¿Marcan los dos equipos?"
        subtitle="Mercado BTTS (Both Teams To Score)"
      >
        <div className="grid grid-cols-2 gap-3">
          <BigOption label={`${home} y ${away} marcan`} prob={btts.yes} highlight />
          <BigOption label="Al menos uno no marca" prob={btts.no} highlight />
        </div>
      </SectionCard>

      {/* ── 5. Resultado al descanso ── */}
      <SectionCard
        icon="⏱️"
        title="¿Cómo termina el primer tiempo?"
        subtitle="Aproximadamente el 38% de los goles caen en la primera mitad"
      >
        <div className="grid grid-cols-3 gap-2">
          <BigOption label={`Gana ${home}`} prob={ht.home_win} highlight />
          <BigOption label="Empate"         prob={ht.draw}     highlight />
          <BigOption label={`Gana ${away}`} prob={ht.away_win} highlight />
        </div>
      </SectionCard>

      {/* ── 6. Goles por equipo ── */}
      <SectionCard
        icon="🥅"
        title="¿Cuántos goles mete cada equipo?"
        subtitle="Probabilidad de que cada equipo llegue a esa cifra de goles"
      >
        <div className="space-y-4">
          <div>
            <p className="text-xs font-semibold text-blue-400 mb-2">{homeTeam}</p>
            <div className="space-y-2">
              <GoalLineRow
                question="¿Marca al menos 1 gol?"
                overProb={hg.home_over_0_5}
                underLabel="No marca"
                underProb={hg.home_under_0_5}
              />
              <GoalLineRow
                question="¿Marca al menos 2 goles?"
                overProb={hg.home_over_1_5}
                underLabel="Marca 0 o 1"
                underProb={hg.home_under_1_5}
              />
            </div>
          </div>
          <div className="border-t border-white/8 pt-4">
            <p className="text-xs font-semibold text-purple-400 mb-2">{awayTeam}</p>
            <div className="space-y-2">
              <GoalLineRow
                question="¿Marca al menos 1 gol?"
                overProb={ag.away_over_0_5}
                underLabel="No marca"
                underProb={ag.away_under_0_5}
              />
              <GoalLineRow
                question="¿Marca al menos 2 goles?"
                overProb={ag.away_over_1_5}
                underLabel="Marca 0 o 1"
                underProb={ag.away_under_1_5}
              />
            </div>
          </div>
        </div>
      </SectionCard>

      {/* ── 7. Portería a cero ── */}
      <SectionCard
        icon="🧤"
        title="¿Algún equipo deja su portería a cero?"
        subtitle="Probabilidad de que el rival no le marque ningún gol"
      >
        <div className="space-y-2">
          {[
            { label: `${homeTeam} no recibe ningún gol`, prob: hcs.yes },
            { label: `${awayTeam} no recibe ningún gol`, prob: acs.yes },
          ].map(({ label, prob }) => {
            const conf = confidence(prob);
            return (
              <div key={label}
                className={`rounded-xl border px-4 py-3 flex items-center justify-between ${probBg(prob)}`}>
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full flex-shrink-0 ${conf.dot}`} />
                  <span className="text-sm text-gray-300">{label}</span>
                </div>
                <div className="text-right flex-shrink-0 ml-3">
                  <span className={`text-lg font-black ${probColor(prob)}`}>{prob}%</span>
                  <p className="text-xs text-gray-600">{conf.label} · {mo(prob)}</p>
                </div>
              </div>
            );
          })}
        </div>
      </SectionCard>

      {/* ── Aviso ── */}
      <p className="text-center text-gray-600 text-xs px-4">
        Probabilidades calculadas con distribución de Poisson · Solo con fines informativos
      </p>
    </div>
  );
}
