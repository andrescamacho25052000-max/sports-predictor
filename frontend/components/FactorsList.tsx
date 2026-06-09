"use client";

import { CheckCircle2, Minus, TrendingUp, TrendingDown, Shield, Home, Users, History, Activity } from "lucide-react";
import { Factor } from "@/lib/api";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";

interface Props {
  factors: Factor[];
  homeTeam: string;
  awayTeam: string;
}

const FACTOR_ICONS: Record<string, React.ElementType> = {
  "Forma reciente":      Activity,
  "Ventaja de localía":  Home,
  "Historial H2H":       History,
  "Ranking / posición":  TrendingUp,
  "Lesionados":          Shield,
  "Plantilla":           Users,
};

function getIcon(name: string): React.ElementType {
  for (const [key, icon] of Object.entries(FACTOR_ICONS)) {
    if (name.toLowerCase().includes(key.toLowerCase())) return icon;
  }
  return Activity;
}

export default function FactorsList({ factors, homeTeam, awayTeam }: Props) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <TrendingUp className="w-4 h-4 text-emerald-400" />
        <h3 className="text-base font-bold text-white">Factores clave</h3>
      </div>

      <div className="space-y-2">
        {factors.map((factor) => {
          const isHome  = factor.advantage === homeTeam;
          const isAway  = factor.advantage === awayTeam;
          const isEqual = !isHome && !isAway;
          const Icon = getIcon(factor.name);

          return (
            <div
              key={factor.name}
              className={cn(
                "rounded-xl p-3.5 border transition-colors",
                isHome  ? "bg-emerald-500/5  border-emerald-500/20" :
                isAway  ? "bg-indigo-500/5   border-indigo-500/20"  :
                          "bg-white/5        border-white/10"
              )}
            >
              <div className="flex items-start gap-3">
                {/* Icono */}
                <div className={cn(
                  "p-1.5 rounded-lg flex-shrink-0 mt-0.5",
                  isHome  ? "bg-emerald-500/15 text-emerald-400" :
                  isAway  ? "bg-indigo-500/15  text-indigo-400"  :
                            "bg-white/10       text-gray-400"
                )}>
                  <Icon className="w-3.5 h-3.5" />
                </div>

                {/* Contenido */}
                <div className="flex-1 min-w-0 space-y-1.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-white font-semibold text-sm">{factor.name}</span>
                    {isEqual ? (
                      <span className="flex items-center gap-1 text-gray-500 text-xs">
                        <Minus className="w-3 h-3" /> Igual
                      </span>
                    ) : (
                      <span className={cn(
                        "flex items-center gap-1 text-xs font-semibold",
                        isHome ? "text-emerald-400" : "text-indigo-400"
                      )}>
                        <CheckCircle2 className="w-3 h-3" />
                        {factor.advantage}
                      </span>
                    )}
                  </div>

                  <p className="text-gray-400 text-xs leading-relaxed">{factor.detail}</p>

                  {/* Barra de peso */}
                  <div className="flex items-center gap-2 pt-0.5">
                    <Progress
                      value={factor.weight}
                      className="h-1 flex-1"
                      indicatorClassName={isHome ? "bg-emerald-500" : isAway ? "bg-indigo-500" : "bg-gray-500"}
                    />
                    <span className="text-gray-600 text-xs flex-shrink-0">{factor.weight}%</span>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
