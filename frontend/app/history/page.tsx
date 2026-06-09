"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  History,
  CheckCircle2,
  XCircle,
  Clock,
  TrendingUp,
  Target,
  Trophy,
  ChevronLeft,
  RefreshCw,
  Edit3,
  Brain,
} from "lucide-react";
import { supabase, type Prediction } from "@/lib/supabase";
import Link from "next/link";

/* ── Helpers ──────────────────────────────────────────────────────────────── */
function fmt(dateStr: string | null) {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString("es-CO", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function TeamCrest({
  src,
  name,
  size = 32,
}: {
  src?: string | null;
  name: string;
  size?: number;
}) {
  const [err, setErr] = useState(false);
  if (src && !err) {
    return (
      <img
        src={src}
        alt={name}
        width={size}
        height={size}
        className="object-contain"
        onError={() => setErr(true)}
      />
    );
  }
  return (
    <div
      className="rounded-full bg-white/10 flex items-center justify-center font-bold text-white/70 text-xs flex-shrink-0"
      style={{ width: size, height: size }}
    >
      {name.slice(0, 2).toUpperCase()}
    </div>
  );
}

/* ── Modal para ingresar resultado ──────────────────────────────────────── */
function ResultModal({
  prediction,
  onClose,
  onSaved,
}: {
  prediction: Prediction;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [homeGoals, setHomeGoals] = useState("");
  const [awayGoals, setAwayGoals] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function handleSave() {
    const h = parseInt(homeGoals);
    const a = parseInt(awayGoals);
    if (isNaN(h) || isNaN(a) || h < 0 || a < 0) {
      setError("Ingresa goles válidos (0 o más)");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/predictions/${prediction.id}/result`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ home_goals: h, away_goals: a }),
        }
      );
      if (!res.ok) throw new Error("Error del servidor");
      onSaved();
      onClose();
    } catch (e) {
      setError("No se pudo guardar el resultado");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.9 }}
        className="bg-gray-900 border border-white/10 rounded-2xl p-6 w-full max-w-sm mx-4 shadow-2xl"
      >
        <h3 className="text-lg font-semibold text-white mb-1">
          Registrar resultado
        </h3>
        <p className="text-sm text-white/50 mb-5">
          {prediction.home_team} vs {prediction.away_team}
        </p>

        <div className="flex items-center gap-3 mb-5">
          <div className="flex-1">
            <label className="block text-xs text-white/50 mb-1">
              {prediction.home_team}
            </label>
            <input
              type="number"
              min={0}
              value={homeGoals}
              onChange={(e) => setHomeGoals(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-center text-xl font-bold focus:outline-none focus:border-emerald-500"
              placeholder="0"
            />
          </div>
          <span className="text-white/30 text-xl font-bold pt-5">—</span>
          <div className="flex-1">
            <label className="block text-xs text-white/50 mb-1">
              {prediction.away_team}
            </label>
            <input
              type="number"
              min={0}
              value={awayGoals}
              onChange={(e) => setAwayGoals(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-center text-xl font-bold focus:outline-none focus:border-emerald-500"
              placeholder="0"
            />
          </div>
        </div>

        {error && <p className="text-red-400 text-sm mb-3">{error}</p>}

        <div className="flex gap-2">
          <button
            onClick={onClose}
            className="flex-1 py-2 rounded-xl bg-white/5 text-white/70 hover:bg-white/10 transition-colors"
          >
            Cancelar
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex-1 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-medium transition-colors disabled:opacity-50"
          >
            {saving ? "Guardando..." : "Guardar"}
          </button>
        </div>
      </motion.div>
    </div>
  );
}

/* ── Tarjeta de predicción ───────────────────────────────────────────────── */
function PredictionCard({
  p,
  onUpdate,
}: {
  p: Prediction;
  onUpdate: () => void;
}) {
  const [showModal, setShowModal] = useState(false);

  const statusColor =
    p.was_correct === true
      ? "border-emerald-500/30 bg-emerald-500/5"
      : p.was_correct === false
      ? "border-red-500/30 bg-red-500/5"
      : "border-white/10 bg-white/3";

  const StatusIcon =
    p.was_correct === true
      ? CheckCircle2
      : p.was_correct === false
      ? XCircle
      : Clock;

  const statusIconColor =
    p.was_correct === true
      ? "text-emerald-400"
      : p.was_correct === false
      ? "text-red-400"
      : "text-white/30";

  return (
    <>
      <motion.div
        layout
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className={`border rounded-2xl p-4 ${statusColor}`}
      >
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2">
            <StatusIcon size={16} className={statusIconColor} />
            <span className="text-xs text-white/40">
              {p.league || "Liga"} · {fmt(p.match_date || p.created_at)}
            </span>
          </div>
          <span className="text-xs text-white/30"># {p.id}</span>
        </div>

        {/* Teams */}
        <div className="flex items-center gap-3 mb-3">
          <div className="flex items-center gap-2 flex-1">
            <TeamCrest src={p.home_crest} name={p.home_team} size={28} />
            <span className="font-semibold text-white text-sm truncate">
              {p.home_team}
            </span>
          </div>
          <div className="text-white/30 text-xs font-bold">vs</div>
          <div className="flex items-center gap-2 flex-1 justify-end">
            <span className="font-semibold text-white text-sm truncate text-right">
              {p.away_team}
            </span>
            <TeamCrest src={p.away_crest} name={p.away_team} size={28} />
          </div>
        </div>

        {/* Prediction & Result row */}
        <div className="flex items-center justify-between">
          <div>
            <span className="text-xs text-white/40">Predicción: </span>
            <span className="text-xs font-medium text-emerald-400">
              {p.pred_winner || "—"}
            </span>
            {p.confidence && (
              <span className="ml-1 text-xs text-white/30">
                ({p.confidence.toFixed(0)}%)
              </span>
            )}
          </div>

          {p.result_actual ? (
            <div className="text-xs">
              <span className="text-white/40">Real: </span>
              <span className="font-medium text-white">
                {p.result_home_goals} — {p.result_away_goals}
              </span>
              <span className="ml-1 text-white/40">({p.result_actual})</span>
            </div>
          ) : (
            <button
              onClick={() => setShowModal(true)}
              className="flex items-center gap-1 text-xs text-white/40 hover:text-emerald-400 transition-colors border border-white/10 hover:border-emerald-500/30 rounded-lg px-2 py-1"
            >
              <Edit3 size={11} />
              Resultado
            </button>
          )}
        </div>
      </motion.div>

      <AnimatePresence>
        {showModal && (
          <ResultModal
            prediction={p}
            onClose={() => setShowModal(false)}
            onSaved={onUpdate}
          />
        )}
      </AnimatePresence>
    </>
  );
}

/* ── Stats bar ───────────────────────────────────────────────────────────── */
function StatsBar({
  total,
  evaluated,
  correct,
  accuracy,
}: {
  total: number;
  evaluated: number;
  correct: number;
  accuracy: number | null;
}) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
      {[
        {
          label: "Total predicciones",
          value: total,
          icon: Target,
          color: "text-white",
        },
        {
          label: "Evaluadas",
          value: evaluated,
          icon: History,
          color: "text-blue-400",
        },
        {
          label: "Correctas",
          value: correct,
          icon: Trophy,
          color: "text-emerald-400",
        },
        {
          label: "Precisión",
          value: accuracy != null ? `${accuracy}%` : "—",
          icon: TrendingUp,
          color: "text-yellow-400",
        },
      ].map(({ label, value, icon: Icon, color }) => (
        <div
          key={label}
          className="bg-white/5 border border-white/10 rounded-2xl p-4 text-center"
        >
          <Icon size={20} className={`${color} mx-auto mb-1`} />
          <div className={`text-2xl font-bold ${color}`}>{value}</div>
          <div className="text-xs text-white/40 mt-1">{label}</div>
        </div>
      ))}
    </div>
  );
}

/* ── Panel de evolución del modelo ──────────────────────────────────────── */
function ModelEvolution({ evolution }: { evolution: any }) {
  if (!evolution || !evolution.history?.length) return null;
  const last = evolution.history[evolution.history.length - 1];
  return (
    <div className="bg-indigo-950/40 border border-indigo-500/20 rounded-2xl p-4 mb-6">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Brain size={16} className="text-indigo-400" />
          <span className="text-sm font-semibold text-white">Evolución del modelo</span>
          <span className="text-xs bg-indigo-500/20 text-indigo-300 px-2 py-0.5 rounded-full">
            v{evolution.current_version}
          </span>
        </div>
        <span className="text-xs text-white/40">{evolution.total_trained} ejemplos acumulados</span>
      </div>
      <div className="flex gap-4 flex-wrap">
        {evolution.history.slice(-5).map((h: any, i: number) => (
          <div key={i} className="text-center">
            <div className={`text-lg font-bold ${h.improvement > 0 ? "text-emerald-400" : "text-white/60"}`}>
              {(h.acc_after * 100).toFixed(0)}%
            </div>
            <div className="text-xs text-white/30">
              {h.improvement != null ? (h.improvement > 0 ? `+${(h.improvement*100).toFixed(1)}%` : `${(h.improvement*100).toFixed(1)}%`) : "base"}
            </div>
            <div className="text-xs text-white/20 mt-0.5">v{h.version}</div>
          </div>
        ))}
        <div className="ml-auto self-center text-xs text-white/30">
          Últimos {Math.min(5, evolution.history.length)} entrenamientos
        </div>
      </div>
    </div>
  );
}

/* ── Page ────────────────────────────────────────────────────────────────── */
export default function HistoryPage() {
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [stats, setStats] = useState<{
    total_predictions: number;
    evaluated: number;
    correct: number;
    accuracy: number | null;
  } | null>(null);
  const [evolution, setEvolution] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);
  const [retraining, setRetraining] = useState(false);
  const [checkMsg, setCheckMsg] = useState("");
  const [filter, setFilter] = useState<"all" | "pending" | "correct" | "wrong">(
    "all"
  );

  async function checkResults() {
    setChecking(true);
    setCheckMsg("");
    try {
      const res = await fetch("${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/predictions/check-results", { method: "POST" });
      const data = await res.json();
      setCheckMsg(data.message);
      if (data.updated > 0) await load();
    } catch {
      setCheckMsg("Error al conectar con el servidor");
    } finally {
      setChecking(false);
      setTimeout(() => setCheckMsg(""), 5000);
    }
  }

  async function load() {
    setLoading(true);
    try {
      const [predRes, statsRes, evoRes] = await Promise.all([
        fetch("${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/predictions?limit=100"),
        fetch("${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/predictions/stats"),
        fetch("${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/predictions/model-evolution"),
      ]);
      const predData  = await predRes.json();
      const statsData = await statsRes.json();
      const evoData   = await evoRes.json();
      setPredictions(predData.predictions || []);
      setStats(statsData);
      setEvolution(evoData);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const filtered = predictions.filter((p) => {
    if (filter === "pending") return p.result_actual === null;
    if (filter === "correct") return p.was_correct === true;
    if (filter === "wrong") return p.was_correct === false;
    return true;
  });

  return (
    <div className="min-h-screen bg-gray-950 text-white pb-24 sm:pb-8">
      <div className="max-w-3xl mx-auto px-4 py-5 sm:py-8">

        {/* Header */}
        <div className="flex items-center justify-between mb-5 sm:mb-6 gap-2">
          <div className="flex items-center gap-2 sm:gap-3 min-w-0">
            <Link href="/" className="p-2 rounded-xl bg-white/5 hover:bg-white/10 transition-colors flex-shrink-0">
              <ChevronLeft size={18} />
            </Link>
            <div className="min-w-0">
              <h1 className="text-base sm:text-xl font-bold flex items-center gap-1.5">
                <History size={18} className="text-emerald-400 flex-shrink-0" />
                <span className="truncate">Historial</span>
              </h1>
              <p className="text-xs text-white/40 hidden sm:block">Registro completo · Supabase</p>
            </div>
          </div>

          {/* Acciones — en mobile se colapsan a iconos */}
          <div className="flex items-center gap-1.5 sm:gap-2 flex-shrink-0">
            {checkMsg && (
              <motion.span
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                className="text-xs text-emerald-400 hidden sm:block"
              >
                {checkMsg}
              </motion.span>
            )}
            <button
              onClick={async () => {
                setRetraining(true);
                try {
                  const r = await fetch("${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/predictions/retrain", { method: "POST", headers: {"Content-Type":"application/json"}, body: '{}' });
                  const d = await r.json();
                  setCheckMsg(d.status === "trained" ? `Modelo v${d.new_version} — ${d.accuracy_after}%` : d.message || d.status);
                  if (d.status === "trained") await load();
                } catch { setCheckMsg("Error al reentrenar"); }
                setRetraining(false);
                setTimeout(() => setCheckMsg(""), 6000);
              }}
              disabled={retraining}
              title="Reentrenar modelo"
              className="flex items-center gap-1 px-2 sm:px-3 py-2 rounded-xl bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/20 text-indigo-400 text-xs transition-colors disabled:opacity-50"
            >
              <Brain size={13} className={retraining ? "animate-pulse" : ""} />
              <span className="hidden sm:inline">{retraining ? "Entrenando..." : "Reentrenar"}</span>
            </button>
            <button
              onClick={checkResults}
              disabled={checking}
              title="Buscar resultados"
              className="flex items-center gap-1 px-2 sm:px-3 py-2 rounded-xl bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-500/20 text-emerald-400 text-xs transition-colors disabled:opacity-50"
            >
              <RefreshCw size={13} className={checking ? "animate-spin" : ""} />
              <span className="hidden sm:inline">{checking ? "Buscando..." : "Buscar resultados"}</span>
            </button>
            <button onClick={load} disabled={loading} className="p-2 rounded-xl bg-white/5 hover:bg-white/10 transition-colors disabled:opacity-50">
              <RefreshCw size={15} className={loading ? "animate-spin" : ""} />
            </button>
          </div>
        </div>

        {/* Mensaje de acción en mobile */}
        {checkMsg && (
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="sm:hidden text-xs text-emerald-400 text-center mb-3">
            {checkMsg}
          </motion.p>
        )}

        {/* Stats */}
        {stats && (
          <StatsBar
            total={stats.total_predictions}
            evaluated={stats.evaluated}
            correct={stats.correct}
            accuracy={stats.accuracy}
          />
        )}

        {/* Evolución del modelo */}
        <ModelEvolution evolution={evolution} />

        {/* Filters */}
        <div className="flex gap-2 mb-4 flex-wrap">
          {(
            [
              { key: "all", label: "Todas" },
              { key: "pending", label: "Pendientes" },
              { key: "correct", label: "Correctas" },
              { key: "wrong", label: "Incorrectas" },
            ] as const
          ).map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setFilter(key)}
              className={`px-3 py-1.5 rounded-xl text-sm font-medium transition-colors ${
                filter === key
                  ? "bg-emerald-600 text-white"
                  : "bg-white/5 text-white/50 hover:bg-white/10"
              }`}
            >
              {label}
            </button>
          ))}
          <span className="ml-auto text-xs text-white/30 self-center">
            {filtered.length} resultado{filtered.length !== 1 ? "s" : ""}
          </span>
        </div>

        {/* List */}
        {loading ? (
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div
                key={i}
                className="h-28 rounded-2xl bg-white/5 animate-pulse"
              />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-16 text-white/30">
            <History size={40} className="mx-auto mb-3 opacity-30" />
            <p className="text-sm">
              {filter === "all"
                ? "Aún no hay predicciones guardadas. ¡Analiza un partido!"
                : "No hay predicciones en esta categoría."}
            </p>
            {filter === "all" && (
              <Link
                href="/"
                className="mt-4 inline-block text-emerald-400 text-sm hover:underline"
              >
                Ir al inicio →
              </Link>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            {filtered.map((p) => (
              <PredictionCard key={p.id} p={p} onUpdate={load} />
            ))}
          </div>
        )}
      </div>

      {/* ── Bottom nav (solo mobile) ── */}
      <nav className="fixed bottom-0 left-0 right-0 sm:hidden bg-gray-950/95 backdrop-blur border-t border-white/10 flex z-50">
        <Link href="/" className="flex-1 flex flex-col items-center gap-1 py-3 text-white/40 hover:text-white/70 transition-colors">
          <TrendingUp size={20} />
          <span className="text-xs">Predecir</span>
        </Link>
        <Link href="/history" className="flex-1 flex flex-col items-center gap-1 py-3 text-emerald-400">
          <History size={20} />
          <span className="text-xs font-medium">Historial</span>
        </Link>
      </nav>
    </div>
  );
}
