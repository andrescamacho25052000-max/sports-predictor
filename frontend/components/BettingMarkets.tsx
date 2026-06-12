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

/* ─── componente principal ───────────────────────────────────────────────── */

export default function BettingMarkets({ poisson, homeTeam, awayTeam }: Props) {
  const { expected_goals: xg, exact_score } = poisson;

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

      {/* ── Aviso ── */}
      <p className="text-center text-gray-600 text-xs px-4">
        Probabilidades calculadas con distribución de Poisson · Solo con fines informativos
      </p>
    </div>
  );
}
