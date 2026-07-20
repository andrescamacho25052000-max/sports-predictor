"use client";

import { useEffect, useState } from "react";
import { Users, CheckCircle2, XCircle, Clock } from "lucide-react";
import { fetchRecentPublic, PredictionRecord } from "@/lib/api";

/**
 * Historial general público: últimos 10 partidos distintos predichos.
 * Visible para todos, sin mostrar quién generó cada predicción.
 */
export default function GeneralHistory() {
  const [preds, setPreds] = useState<PredictionRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRecentPublic(10)
      .then(setPreds)
      .catch(() => setPreds([]))
      .finally(() => setLoading(false));
  }, []);

  if (!loading && preds.length === 0) return null;

  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <Users className="w-4 h-4 text-emerald-400" />
        <h3 className="text-base font-bold text-white">Últimas predicciones de la comunidad</h3>
      </div>

      {loading ? (
        <div className="space-y-2">
          {[...Array(4)].map((_, i) => <div key={i} className="h-11 rounded-xl bg-white/5 animate-pulse" />)}
        </div>
      ) : (
        <div className="space-y-1.5">
          {preds.map((p) => {
            const Icon = p.result_actual == null ? Clock : p.was_correct ? CheckCircle2 : XCircle;
            const color = p.result_actual == null ? "text-white/30" : p.was_correct ? "text-emerald-400" : "text-red-400";
            return (
              <div key={p.id} className="flex items-center gap-2.5 bg-white/5 border border-white/10 rounded-xl px-3 py-2">
                <Icon size={15} className={`${color} flex-shrink-0`} />
                <span className="text-white/85 text-sm flex-1 min-w-0 truncate">
                  {p.home_team} <span className="text-white/30">vs</span> {p.away_team}
                </span>
                <span className="text-xs text-emerald-400/80 font-medium hidden sm:inline">{p.pred_winner}</span>
                {p.result_actual != null && (
                  <span className="text-xs text-white/40 w-12 text-right">
                    {p.result_home_goals}–{p.result_away_goals}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
