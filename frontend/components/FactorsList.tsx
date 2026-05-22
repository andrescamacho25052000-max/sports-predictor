"use client";

import { Factor } from "@/lib/api";

interface Props {
  factors: Factor[];
  homeTeam: string;
  awayTeam: string;
}

const advantageColor = (advantage: string, homeTeam: string, awayTeam: string) => {
  if (advantage === homeTeam) return "text-emerald-400";
  if (advantage === awayTeam) return "text-blue-400";
  return "text-gray-400";
};

const advantageIcon = (advantage: string, homeTeam: string, awayTeam: string) => {
  if (advantage === homeTeam) return "✓";
  if (advantage === awayTeam) return "✓";
  return "—";
};

export default function FactorsList({ factors, homeTeam, awayTeam }: Props) {
  return (
    <div className="space-y-3">
      <h3 className="text-lg font-semibold text-white">Factores clave</h3>
      <div className="space-y-2">
        {factors.map((factor) => (
          <div
            key={factor.name}
            className="bg-white/5 rounded-xl p-3 flex items-start gap-3 border border-white/10"
          >
            <div className="flex-shrink-0 mt-0.5">
              <span className={`text-lg ${advantageColor(factor.advantage, homeTeam, awayTeam)}`}>
                {advantageIcon(factor.advantage, homeTeam, awayTeam)}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <span className="text-white font-medium text-sm">{factor.name}</span>
                <span className="text-gray-400 text-xs flex-shrink-0">Peso {factor.weight}%</span>
              </div>
              <p className="text-gray-400 text-xs mt-0.5 line-clamp-2">{factor.detail}</p>
              {factor.advantage !== "Igual" && (
                <span className={`text-xs font-semibold mt-0.5 inline-block ${advantageColor(factor.advantage, homeTeam, awayTeam)}`}>
                  Ventaja: {factor.advantage}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
