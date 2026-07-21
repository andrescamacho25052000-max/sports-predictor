"use client";

import { useEffect, useState } from "react";
import { Activity, Target, Trophy, CalendarDays, type LucideIcon } from "lucide-react";
import { fetchStats, fetchLeagues, fetchUpcoming } from "@/lib/api";

interface Kpi {
  label: string;
  value: string;
  sub: string;
  icon: LucideIcon;
  accent?: boolean;
}

function fmt(n: number): string {
  return n.toLocaleString("es-ES");
}

/**
 * Fila de 4 KPIs de la home (estilo Statix). Todas las cifras son reales y en
 * vivo desde el backend; nada de valores inflados (ver doc. 18.5).
 */
export default function KpiRow() {
  const [kpis, setKpis] = useState<Kpi[] | null>(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      const [stats, leagues, upcoming] = await Promise.allSettled([
        fetchStats(),
        fetchLeagues(),
        fetchUpcoming(),
      ]);
      if (!alive) return;

      const s = stats.status === "fulfilled" ? stats.value : null;
      const l = leagues.status === "fulfilled" ? leagues.value : [];
      const u = upcoming.status === "fulfilled" ? upcoming.value.matches : [];

      // El backend ya devuelve la precisión como porcentaje (0-100).
      const acc = s && s.accuracy != null ? `${s.accuracy.toFixed(1)}%` : "—";

      setKpis([
        {
          label: "Predicciones",
          value: s ? fmt(s.total_predictions) : "—",
          sub: s ? `${fmt(s.evaluated)} con resultado` : "track record",
          icon: Activity,
        },
        {
          label: "Aciertos 1X2",
          value: acc,
          sub: s ? `${fmt(s.evaluated)} evaluados · en vivo` : "en vivo",
          icon: Target,
          accent: true,
        },
        {
          label: "Ligas cubiertas",
          value: l.length ? fmt(l.length) : "—",
          sub: "fútbol · NBA",
          icon: Trophy,
        },
        {
          label: "Próximos partidos",
          value: fmt(u.length),
          sub: "en agenda",
          icon: CalendarDays,
        },
      ]);
    })();
    return () => {
      alive = false;
    };
  }, []);

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
      {(kpis ?? Array.from({ length: 4 })).map((k, i) => {
        const Icon = k?.icon ?? Activity;
        return (
          <div
            key={k?.label ?? i}
            className="rounded-2xl border border-border bg-surface p-4 sm:p-5"
          >
            <div className="flex items-start justify-between gap-2">
              <p className="eyebrow">{k?.label ?? "—"}</p>
              <span className="grid place-items-center h-8 w-8 rounded-lg bg-accent/15 text-accent shrink-0">
                <Icon size={16} />
              </span>
            </div>
            <p
              className={`mt-3 font-mono text-2xl sm:text-3xl font-bold tracking-tight ${
                k?.accent ? "text-accent" : "text-white"
              } ${k ? "" : "animate-pulse text-muted-2"}`}
            >
              {k?.value ?? "···"}
            </p>
            <p className="mt-1 text-xs text-muted-2">{k?.sub ?? ""}</p>
          </div>
        );
      })}
    </div>
  );
}
