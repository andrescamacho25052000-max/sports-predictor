"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  BarChart3, CheckCircle2, XCircle, Clock, TrendingUp, Target,
  Trophy, ChevronLeft, ShieldCheck, History,
} from "lucide-react";
import Link from "next/link";
import SportSwitcher from "@/components/SportSwitcher";
import {
  fetchStats, fetchMarketStats, fetchRecentPublic,
  GlobalStats, MarketStats, PredictionRecord,
} from "@/lib/api";

/* ── Helpers ──────────────────────────────────────────────────────────────── */
function fmtDate(d: string | null) {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("es-CO", { day: "2-digit", month: "short" });
}

const accColor = (a: number | null) =>
  a == null ? "text-white/40" : a >= 60 ? "text-emerald-400" : a >= 50 ? "text-yellow-400" : "text-orange-400";

/* ── KPI grande ───────────────────────────────────────────────────────────── */
function HeroAccuracy({ stats }: { stats: GlobalStats | null }) {
  return (
    <div className="bg-gradient-to-br from-emerald-500/15 to-emerald-700/5 border border-emerald-500/30 rounded-3xl p-6 sm:p-8 text-center">
      <div className="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-300/80 bg-emerald-500/10 border border-emerald-500/20 rounded-full px-3 py-1 mb-4">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
        Actualizado en vivo
      </div>
      <div className="text-5xl sm:text-7xl font-black text-emerald-400 leading-none">
        {stats?.accuracy != null ? `${stats.accuracy}%` : "—"}
      </div>
      <p className="text-white/60 text-sm mt-3">
        precisión en el resultado (1X2) sobre{" "}
        <span className="text-white font-semibold">{stats?.evaluated ?? 0}</span> partidos ya jugados
      </p>
    </div>
  );
}

/* ── Tarjeta de stat ─────────────────────────────────────────────────────── */
function StatCard({ label, value, icon: Icon, color }: {
  label: string; value: string | number; icon: any; color: string;
}) {
  return (
    <div className="bg-white/5 border border-white/10 rounded-2xl p-4 text-center">
      <Icon size={20} className={`${color} mx-auto mb-1`} />
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
      <div className="text-xs text-white/40 mt-1">{label}</div>
    </div>
  );
}

/* ── Precisión por mercado ──────────────────────────────────────────────── */
function MarketGrid({ market }: { market: MarketStats | null }) {
  if (!market) return null;
  const cards = [
    { label: "Ganador (1X2)", data: market.result_1x2 },
    { label: "Más/Menos 2.5", data: market.over_under_25 },
    { label: "Ambos marcan", data: market.btts },
  ];
  if (!cards.some((c) => c.data?.n > 0)) return null;
  return (
    <div className="bg-white/5 border border-white/10 rounded-2xl p-5">
      <div className="flex items-center gap-2 mb-4">
        <Target size={16} className="text-emerald-400" />
        <span className="text-sm font-semibold text-white">Precisión por tipo de apuesta</span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {cards.map(({ label, data }) => (
          <div key={label} className="bg-white/5 rounded-xl p-4 text-center">
            <div className={`text-3xl font-black ${accColor(data?.accuracy)}`}>
              {data?.accuracy != null ? `${data.accuracy}%` : "—"}
            </div>
            <div className="text-xs text-white/50 mt-1">{label}</div>
            <div className="text-xs text-white/25 mt-0.5">{data?.n || 0} evaluados</div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Precisión por liga ─────────────────────────────────────────────────── */
function LeagueTable({ stats }: { stats: GlobalStats | null }) {
  const leagues = Object.entries(stats?.by_league ?? {})
    .map(([name, v]) => ({ name, ...v, acc: v.total ? (v.correct / v.total) * 100 : 0 }))
    .filter((l) => l.total >= 1)
    .sort((a, b) => b.total - a.total)
    .slice(0, 8);
  if (leagues.length === 0) return null;
  return (
    <div className="bg-white/5 border border-white/10 rounded-2xl p-5">
      <div className="flex items-center gap-2 mb-4">
        <Trophy size={16} className="text-emerald-400" />
        <span className="text-sm font-semibold text-white">Precisión por liga</span>
      </div>
      <div className="space-y-2">
        {leagues.map((l) => (
          <div key={l.name} className="flex items-center gap-3">
            <span className="text-sm text-white/70 flex-1 truncate">{l.name}</span>
            <span className="text-xs text-white/30">{l.correct}/{l.total}</span>
            <div className="w-24 h-1.5 bg-white/10 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${l.acc >= 60 ? "bg-emerald-400" : l.acc >= 50 ? "bg-yellow-400" : "bg-orange-400"}`}
                style={{ width: `${Math.min(100, l.acc)}%` }}
              />
            </div>
            <span className={`text-sm font-bold w-12 text-right ${accColor(l.acc)}`}>
              {l.acc.toFixed(0)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Últimas predicciones evaluadas ─────────────────────────────────────── */
function RecentResults({ preds }: { preds: PredictionRecord[] }) {
  const evaluated = preds.filter((p) => p.result_actual != null).slice(0, 12);
  if (evaluated.length === 0) return null;
  return (
    <div className="bg-white/5 border border-white/10 rounded-2xl p-5">
      <div className="flex items-center gap-2 mb-4">
        <History size={16} className="text-emerald-400" />
        <span className="text-sm font-semibold text-white">Últimos resultados</span>
        <span className="text-xs text-white/30">— sin filtrar, aciertos y fallos</span>
      </div>
      <div className="space-y-1.5">
        {evaluated.map((p) => {
          const Icon = p.was_correct ? CheckCircle2 : XCircle;
          const color = p.was_correct ? "text-emerald-400" : "text-red-400";
          return (
            <div key={p.id} className="flex items-center gap-2 text-sm py-1.5 border-b border-white/5 last:border-0">
              <Icon size={15} className={`${color} flex-shrink-0`} />
              <span className="text-white/80 flex-1 truncate">
                {p.home_team} <span className="text-white/30">vs</span> {p.away_team}
              </span>
              <span className="text-xs text-white/40 hidden sm:inline">{p.pred_winner}</span>
              <span className="text-xs text-white/30 w-14 text-right">
                {p.result_home_goals}–{p.result_away_goals}
              </span>
              <span className="text-xs text-white/25 w-12 text-right hidden sm:inline">{fmtDate(p.match_date)}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ── Page ────────────────────────────────────────────────────────────────── */
export default function TrackRecordPage() {
  const [stats, setStats] = useState<GlobalStats | null>(null);
  const [market, setMarket] = useState<MarketStats | null>(null);
  const [preds, setPreds] = useState<PredictionRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([fetchStats(), fetchMarketStats(), fetchRecentPublic(50)])
      .then(([s, m, p]) => { setStats(s); setMarket(m); setPreds(p); })
      .catch((e) => console.error(e))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-950 via-gray-900 to-emerald-950 text-white pb-24 sm:pb-12">
      <div className="max-w-3xl mx-auto px-4 py-5 sm:py-8 space-y-5">

        {/* Header */}
        <div className="flex items-center gap-3">
          <Link href="/" className="p-2 rounded-xl bg-white/5 hover:bg-white/10 transition-colors flex-shrink-0">
            <ChevronLeft size={18} />
          </Link>
          <div>
            <h1 className="text-lg sm:text-2xl font-black flex items-center gap-2">
              <BarChart3 size={22} className="text-emerald-400" />
              Track record
            </h1>
            <p className="text-xs text-white/40">Historial verificable · todas las predicciones, sin esconder fallos</p>
          </div>
        </div>

        {/* Selector de deporte */}
        <SportSwitcher />

        {loading ? (
          <div className="space-y-4">
            {[...Array(4)].map((_, i) => <div key={i} className="h-32 rounded-2xl bg-white/5 animate-pulse" />)}
          </div>
        ) : (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-5"
          >
            <HeroAccuracy stats={stats} />

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <StatCard label="Predicciones" value={stats?.total_predictions ?? 0} icon={Target} color="text-white" />
              <StatCard label="Evaluadas" value={stats?.evaluated ?? 0} icon={BarChart3} color="text-blue-400" />
              <StatCard label="Aciertos" value={stats?.correct ?? 0} icon={Trophy} color="text-emerald-400" />
              <StatCard label="Pendientes" value={stats?.pending ?? 0} icon={Clock} color="text-white/60" />
            </div>

            <MarketGrid market={market} />
            <LeagueTable stats={stats} />
            <RecentResults preds={preds} />

            {/* Disclaimer de honestidad */}
            <div className="flex items-start gap-2 bg-white/5 border border-white/10 rounded-2xl p-4">
              <ShieldCheck size={16} className="text-emerald-400 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-white/50 leading-relaxed">
                Cada predicción se guarda automáticamente al generarse y su resultado real se
                registra solo cuando termina el partido. Este historial incluye{" "}
                <span className="text-white/70 font-medium">todos</span> los pronósticos —
                aciertos y fallos — sin selección manual. El fútbol tiene alta varianza: ningún
                modelo acierta siempre, y la precisión sobre partidos reales suele ser menor que
                en pruebas de laboratorio.
              </p>
            </div>
          </motion.div>
        )}
      </div>

      {/* ── Bottom nav (solo mobile) ── */}
      <nav className="fixed bottom-0 left-0 right-0 sm:hidden bg-gray-950/95 backdrop-blur border-t border-white/10 flex z-50">
        <Link href="/" className="flex-1 flex flex-col items-center gap-1 py-3 text-white/40 hover:text-white/70 transition-colors">
          <TrendingUp size={20} />
          <span className="text-xs">Predecir</span>
        </Link>
        <Link href="/track-record" className="flex-1 flex flex-col items-center gap-1 py-3 text-emerald-400">
          <BarChart3 size={20} />
          <span className="text-xs font-medium">Récord</span>
        </Link>
        <Link href="/history" className="flex-1 flex flex-col items-center gap-1 py-3 text-white/40 hover:text-white/70 transition-colors">
          <History size={20} />
          <span className="text-xs">Historial</span>
        </Link>
      </nav>
    </div>
  );
}
