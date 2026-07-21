"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Zap, TrendingUp, Lock, Target } from "lucide-react";
import { useAuth } from "@/lib/auth";
import AuthMenu from "@/components/AuthMenu";
import SportSwitcher from "@/components/SportSwitcher";
import {
  fetchNbaTeams, fetchNbaPrediction, NbaTeam, NbaPrediction, OddsMarket,
} from "@/lib/api";
import { cn } from "@/lib/utils";

function fmtEv(ev: number) {
  const p = Math.round(ev * 100);
  return `${p > 0 ? "+" : ""}${p}%`;
}

function ProbBar({ p }: { p: NbaPrediction }) {
  const h = p.probabilities.home_win;
  return (
    <div>
      <div className="flex justify-between text-sm mb-1.5">
        <span className="font-semibold text-white">{p.home_team} <span className="text-white/40">(local)</span></span>
        <span className="font-semibold text-white">{p.away_team}</span>
      </div>
      <div className="flex h-9 rounded-xl overflow-hidden">
        <div className="bg-emerald-500/80 flex items-center justify-start px-3 text-xs font-bold text-white" style={{ width: `${h}%` }}>
          {h.toFixed(1)}%
        </div>
        <div className="bg-indigo-500/70 flex items-center justify-end px-3 text-xs font-bold text-white" style={{ width: `${100 - h}%` }}>
          {(100 - h).toFixed(1)}%
        </div>
      </div>
    </div>
  );
}

function EvBadge({ info }: { info: OddsMarket }) {
  return (
    <span className={cn("text-[10px] font-bold px-1.5 py-0.5 rounded-md",
      info.value ? "bg-emerald-500/20 text-emerald-300" : "bg-red-500/15 text-red-300")}>
      {fmtEv(info.ev)}
    </span>
  );
}

export default function NbaPage() {
  const { session, loading: authLoading } = useAuth();
  const [teams, setTeams] = useState<NbaTeam[]>([]);
  const [home, setHome] = useState("");
  const [away, setAway] = useState("");
  const [pred, setPred] = useState<NbaPrediction | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchNbaTeams().then((d) => setTeams(d.teams)).catch(() => {});
  }, []);

  async function analyze() {
    if (!session) return;
    if (!home || !away || home === away) {
      setError("Elige dos equipos diferentes.");
      return;
    }
    setError("");
    setLoading(true);
    setPred(null);
    try {
      const p = await fetchNbaPrediction(home, away, session.access_token);
      setPred(p);
    } catch {
      setError("No se pudo obtener la predicción. ¿El backend está corriendo?");
    } finally {
      setLoading(false);
    }
  }

  const ouRows = pred ? Object.entries(pred.over_under) : [];
  const keyHandicaps = pred
    ? ["home_-5.5", "home_-3.5", "home_-1.5", "away_+1.5", "away_+3.5", "away_+5.5"]
        .filter((k) => pred.handicap[k] != null)
        .map((k) => ({ k, v: pred.handicap[k] }))
    : [];

  return (
    <main className="min-h-screen bg-gradient-to-br from-gray-950 via-gray-900 to-orange-950/40 text-white px-4 py-5 sm:py-8 pb-24 sm:pb-8">
      <div className="max-w-3xl mx-auto space-y-5">

        {/* Header */}
        <div className="flex items-center justify-between gap-2">
          <h1 className="text-lg sm:text-2xl font-black flex items-center gap-2">
            🏀 NBA <span className="text-xs font-medium text-white/40 hidden sm:inline">Elo + totales + hándicap</span>
          </h1>
          <AuthMenu />
        </div>

        {/* Selector de deporte */}
        <SportSwitcher />

        {authLoading ? null : !session ? (
          <div className="bg-white/5 border border-white/10 rounded-3xl p-10 flex flex-col items-center gap-4 text-center">
            <Lock size={32} className="text-white/30" />
            <p className="text-white font-semibold">Inicia sesión para analizar partidos de NBA</p>
            <AuthMenu />
          </div>
        ) : (
          <>
            {/* Selector de equipos */}
            <div className="bg-white/5 border border-white/10 rounded-3xl p-4 sm:p-6 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-white/50 mb-1">Local</label>
                  <select value={home} onChange={(e) => setHome(e.target.value)}
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-emerald-500">
                    <option value="">Elige equipo…</option>
                    {teams.map((t) => <option key={t.name} value={t.name} className="bg-gray-900">{t.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-white/50 mb-1">Visitante</label>
                  <select value={away} onChange={(e) => setAway(e.target.value)}
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-emerald-500">
                    <option value="">Elige equipo…</option>
                    {teams.map((t) => <option key={t.name} value={t.name} className="bg-gray-900">{t.name}</option>)}
                  </select>
                </div>
              </div>
              {error && <p className="text-red-400 text-sm">{error}</p>}
              <button onClick={analyze} disabled={loading}
                className="w-full py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold transition-colors disabled:opacity-50">
                {loading ? "Analizando…" : "Analizar partido"}
              </button>
            </div>

            {/* Resultado */}
            {pred && (
              <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
                <div className="bg-white/5 border border-white/10 rounded-3xl p-4 sm:p-6 space-y-5">
                  <ProbBar p={pred} />

                  <div className="grid grid-cols-3 gap-3 text-center">
                    <div className="bg-white/5 rounded-xl p-3">
                      <div className="text-xl font-bold text-emerald-400">{pred.expected_points.home}</div>
                      <div className="text-xs text-white/40">pts local</div>
                    </div>
                    <div className="bg-white/5 rounded-xl p-3">
                      <div className="text-xl font-bold text-white">{pred.expected_points.total}</div>
                      <div className="text-xs text-white/40">total esperado</div>
                    </div>
                    <div className="bg-white/5 rounded-xl p-3">
                      <div className="text-xl font-bold text-indigo-400">{pred.expected_points.away}</div>
                      <div className="text-xs text-white/40">pts visitante</div>
                    </div>
                  </div>
                  <p className="text-center text-xs text-white/40">
                    Margen esperado: {pred.expected_points.margin > 0 ? "+" : ""}{pred.expected_points.margin} para el local ·
                    Elo {pred.elo.home} vs {pred.elo.away}
                  </p>
                </div>

                {/* Over / Under */}
                <div className="bg-white/5 border border-white/10 rounded-3xl p-4 sm:p-6">
                  <div className="flex items-center gap-2 mb-3">
                    <Target size={16} className="text-sky-400" />
                    <h3 className="text-sm font-bold text-white">Total de puntos (Over/Under)</h3>
                  </div>
                  <div className="space-y-1.5">
                    {ouRows.map(([line, d]) => (
                      <div key={line} className="flex items-center gap-3 text-sm bg-white/5 rounded-lg px-3 py-2">
                        <span className="text-white/70 w-20">Línea {line}</span>
                        <span className="text-emerald-400 flex-1">Más: <b>{d.over}%</b></span>
                        <span className="text-indigo-300 flex-1">Menos: <b>{d.under}%</b></span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Hándicap */}
                {keyHandicaps.length > 0 && (
                  <div className="bg-white/5 border border-white/10 rounded-3xl p-4 sm:p-6">
                    <div className="flex items-center gap-2 mb-3">
                      <TrendingUp size={16} className="text-cyan-400" />
                      <h3 className="text-sm font-bold text-white">Hándicap (spread)</h3>
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                      {keyHandicaps.map(({ k, v }) => {
                        const label = k.startsWith("home_")
                          ? `${pred.home_team} ${k.slice(5)}`
                          : `${pred.away_team} ${k.slice(5)}`;
                        return (
                          <div key={k} className="bg-white/5 rounded-lg px-3 py-2 text-sm">
                            <div className="text-white/60 text-xs truncate">{label}</div>
                            <div className="font-bold text-white">{v}%</div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Cuotas reales + EV */}
                {pred.odds ? (
                  <div className="bg-gradient-to-br from-emerald-500/15 to-emerald-700/5 border border-emerald-500/30 rounded-3xl p-4 sm:p-6">
                    <div className="flex items-center gap-2 mb-3">
                      <Zap size={16} className="text-emerald-400" />
                      <h3 className="text-sm font-bold text-emerald-300">Cuotas reales + valor (EV)</h3>
                      <span className="text-[11px] text-emerald-400/60">{pred.odds.bookmaker_count} casas</span>
                    </div>
                    {pred.odds.best_value.length > 0 ? (
                      <div className="space-y-2">
                        {pred.odds.best_value.map((m) => (
                          <div key={m.market} className="flex items-center justify-between bg-emerald-500/10 rounded-xl px-3 py-2">
                            <span className="text-white text-sm font-medium">{m.market}</span>
                            <div className="flex items-center gap-2">
                              <span className="text-white text-sm font-bold">{m.odds.toFixed(2)}</span>
                              <EvBadge info={m} />
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-white/50 text-sm">Cuotas analizadas: ningún mercado con valor positivo ahora.</p>
                    )}
                  </div>
                ) : (
                  <p className="text-center text-white/30 text-xs">
                    Sin cuotas reales (configura ODDS_API_KEY y debe haber temporada NBA activa).
                  </p>
                )}

                <p className="text-center text-white/30 text-[11px] leading-relaxed">
                  Modelo: {pred.model} · Elo de temporadas hasta {pred.meta.scoring_season}.
                  Probabilidades estimadas, no garantías.
                </p>
              </motion.div>
            )}
          </>
        )}
      </div>

    </main>
  );
}
