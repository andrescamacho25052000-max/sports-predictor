"use client";

import { CornerCardsData } from "@/lib/api";
import { poissonOver } from "@/lib/markets";

interface Props {
  data: CornerCardsData;
  homeTeam: string;
  awayTeam: string;
}

function pct(n: number) { return `${Math.round(n * 100)}%`; }

/** Cuota mínima para que la apuesta tenga valor (p en fracción 0-1). */
function mo(p: number) {
  if (p <= 0) return "—";
  return `>${(1 / p).toFixed(2)}`;
}

function short(name: string) {
  if (name.length <= 10) return name;
  return name.split(" ").pop() || name.slice(0, 8);
}

function confidence(p: number): string {
  if (p >= 0.65) return "text-emerald-400 bg-emerald-500/10 border-emerald-500/20";
  if (p >= 0.45) return "text-yellow-400 bg-yellow-500/10 border-yellow-500/20";
  if (p >= 0.25) return "text-orange-400 bg-orange-500/10 border-orange-500/20";
  return "text-gray-500 bg-white/5 border-white/10";
}

function StatBadge({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className={`flex flex-col items-center justify-center p-2 sm:p-3 rounded-xl border text-center ${color ?? "bg-white/5 border-white/10"}`}>
      <span className="text-base sm:text-lg font-black">{value}</span>
      <span className="text-xs text-gray-400 mt-0.5 leading-tight">{label}</span>
    </div>
  );
}

function OverUnderGrid({ markets, label }: { markets: Record<string, number>; label: string }) {
  const entries = Object.entries(markets).sort((a, b) => parseFloat(a[0]) - parseFloat(b[0]));
  return (
    <div className="space-y-2">
      <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">{label}</p>
      {/* color de la celda según el lado favorito (over o under) */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5 sm:gap-2">
        {entries.map(([threshold, prob]) => {
          const under = 1 - prob;
          return (
            <div key={threshold}
              className={`rounded-xl border p-2 sm:p-2.5 text-center space-y-0.5 ${confidence(Math.max(prob, under))}`}>
              <div className="text-xs sm:text-sm font-bold">Línea {threshold}</div>
              <div className={`text-xs ${prob >= under ? "font-bold" : "opacity-60"}`}>
                Más: {pct(prob)} <span className="opacity-70">{mo(prob)}</span>
              </div>
              <div className={`text-xs ${under > prob ? "font-bold" : "opacity-60"}`}>
                Menos: {pct(under)} <span className="opacity-70">{mo(under)}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function CornersCards({ data, homeTeam, awayTeam }: Props) {
  const { corners, yellow_cards, fouls } = data;
  const isReal = data.data_source === "statsbomb";
  const H = short(homeTeam);
  const A = short(awayTeam);

  return (
    <div className="bg-white/5 border border-white/10 rounded-3xl p-4 sm:p-6 space-y-6 sm:space-y-8">

      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h2 className="text-white font-bold text-base sm:text-lg">📊 Estadísticas del Partido</h2>
        <span className={`text-xs px-2.5 py-1 rounded-full border font-medium ${
          isReal
            ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
            : "text-gray-400 bg-white/5 border-white/10"
        }`}>
          {isReal ? "✓ StatsBomb" : "Estimación"}
        </span>
      </div>

      {/* ═══ CORNERS ═══ */}
      <div className="space-y-3">
        <h3 className="text-gray-300 font-semibold flex items-center gap-2 text-sm sm:text-base">
          🚩 Tiros de Esquina
        </h3>
        <div className="grid grid-cols-3 gap-2">
          <StatBadge label={H} value={corners.expected_home.toFixed(1)} color="bg-blue-500/10 border-blue-500/20 text-blue-300" />
          <StatBadge label="Total" value={corners.expected_total.toFixed(1)} color="bg-white/5 border-white/10 text-white" />
          <StatBadge label={A} value={corners.expected_away.toFixed(1)} color="bg-purple-500/10 border-purple-500/20 text-purple-300" />
        </div>

        {/* Quién saca más */}
        <div className="grid grid-cols-3 gap-1.5 sm:gap-2">
          <div className={`rounded-xl border p-2 sm:p-3 text-center ${confidence(corners.home_more)}`}>
            <div className="font-bold text-sm">{pct(corners.home_more)}</div>
            <div className="text-xs opacity-70">Más {H}</div>
          </div>
          <div className={`rounded-xl border p-2 sm:p-3 text-center ${confidence(corners.equal)}`}>
            <div className="font-bold text-sm">{pct(corners.equal)}</div>
            <div className="text-xs opacity-70">Igual</div>
          </div>
          <div className={`rounded-xl border p-2 sm:p-3 text-center ${confidence(corners.away_more)}`}>
            <div className="font-bold text-sm">{pct(corners.away_more)}</div>
            <div className="text-xs opacity-70">Más {A}</div>
          </div>
        </div>

        <OverUnderGrid markets={corners.over_under} label="Over/Under corners" />
      </div>

      <div className="border-t border-white/10" />

      {/* ═══ TARJETAS AMARILLAS ═══ */}
      <div className="space-y-3">
        <h3 className="text-gray-300 font-semibold flex items-center gap-2 text-sm sm:text-base">
          🟨 Tarjetas Amarillas
        </h3>
        <div className="grid grid-cols-3 gap-2">
          <StatBadge label={H} value={yellow_cards.expected_home.toFixed(1)} color="bg-yellow-500/10 border-yellow-500/20 text-yellow-300" />
          <StatBadge label="Total" value={yellow_cards.expected_total.toFixed(1)} color="bg-white/5 border-white/10 text-white" />
          <StatBadge label={A} value={yellow_cards.expected_away.toFixed(1)} color="bg-yellow-500/10 border-yellow-500/20 text-yellow-300" />
        </div>
        <OverUnderGrid markets={yellow_cards.over_under} label="Over/Under amarillas" />

        {/* Distribución: apilada en mobile, lado a lado en desktop */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {([["home", homeTeam, yellow_cards.home_dist], ["away", awayTeam, yellow_cards.away_dist]] as const).map(([side, team, dist]) => (
            <div key={side} className="space-y-2">
              <p className="text-xs text-gray-500 font-medium">{team}</p>
              <div className="grid grid-cols-6 gap-1">
                {Object.entries(dist).map(([k, v]) => (
                  <div key={k} className={`rounded-lg border p-1.5 text-center ${confidence(v as number)}`}>
                    <div className="text-xs font-bold">{pct(v as number)}</div>
                    <div className="text-xs opacity-60">{k}🟨</div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="border-t border-white/10" />

      {/* ═══ FALTAS ═══ */}
      <div className="space-y-3">
        <h3 className="text-gray-300 font-semibold flex items-center gap-2 text-sm sm:text-base">
          🦵 Faltas
        </h3>
        <div className="grid grid-cols-3 gap-2">
          <StatBadge label={H} value={fouls.expected_home.toFixed(1)} color="bg-red-500/10 border-red-500/20 text-red-300" />
          <StatBadge label="Total" value={fouls.expected_total.toFixed(1)} color="bg-white/5 border-white/10 text-white" />
          <StatBadge label={A} value={fouls.expected_away.toFixed(1)} color="bg-red-500/10 border-red-500/20 text-red-300" />
        </div>
        {fouls.expected_total > 10 && (
          <OverUnderGrid
            label="Over/Under faltas (Poisson sobre el promedio)"
            markets={Object.fromEntries(
              [-4.5, -2.5, -0.5, 1.5, 3.5].map((off) => {
                const line = Math.round(fouls.expected_total) + off;
                return [String(line), poissonOver(fouls.expected_total, line) / 100];
              })
            )}
          />
        )}
      </div>

      <p className="text-center text-gray-600 text-xs">
        Basado en promedios StatsBomb · Distribución de Poisson
      </p>
    </div>
  );
}
