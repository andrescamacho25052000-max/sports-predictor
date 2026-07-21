"use client";

import { useEffect, useState } from "react";
import { Flame, ArrowUpRight } from "lucide-react";
import { fetchUpcoming, UpcomingMatch } from "@/lib/api";

function formatDate(dateStr?: string): string {
  if (!dateStr) return "";
  return new Date(dateStr)
    .toLocaleDateString("es-ES", {
      weekday: "short",
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    })
    .replace(",", " ·")
    .toUpperCase();
}

/** Iniciales de un equipo para el "escudo" cuando no hay imagen. */
function initials(name: string): string {
  const parts = name.split(/\s+/).filter(Boolean);
  if (parts.length === 1) return parts[0].slice(0, 3).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function Team({ name, crest }: { name: string; crest?: string }) {
  return (
    <div className="flex items-center gap-2.5 min-w-0">
      {crest ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={crest}
          alt=""
          className="h-7 w-7 object-contain shrink-0"
          onError={(e) => {
            (e.target as HTMLImageElement).style.display = "none";
          }}
        />
      ) : (
        <span className="grid place-items-center h-7 w-7 rounded-full bg-white/[0.06] border border-border font-mono text-[10px] font-bold text-white shrink-0">
          {initials(name)}
        </span>
      )}
      <span className="truncate text-sm font-semibold text-white">{name}</span>
    </div>
  );
}

function MatchCard({
  match,
  onSelect,
}: {
  match: UpcomingMatch;
  onSelect: () => void;
}) {
  return (
    <button
      onClick={onSelect}
      className="group text-left rounded-2xl border border-border bg-surface hover:border-border-strong p-4 transition-colors flex flex-col gap-3"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="eyebrow truncate">{match.league}</span>
        <span className="font-mono text-[10px] text-muted-2 shrink-0">
          {formatDate(match.date)}
        </span>
      </div>

      <div className="space-y-2">
        <Team name={match.home} crest={match.home_crest} />
        <Team name={match.away} crest={match.away_crest} />
      </div>

      <div className="mt-auto flex items-center justify-end pt-1 border-t border-border">
        <span className="inline-flex items-center gap-1 text-xs font-medium text-accent group-hover:gap-1.5 transition-all pt-2">
          Ver análisis
          <ArrowUpRight size={14} />
        </span>
      </div>
    </button>
  );
}

/**
 * Sección "Próximos partidos" (estilo Statix). Muestra fixtures reales; la barra
 * 1X2/EV se calcula al abrir el análisis (requiere sesión), por lo que aquí no se
 * inventan probabilidades (ver doc. 18.5).
 */
export default function UpcomingStatix({
  onSelectMatch,
}: {
  onSelectMatch: (m: UpcomingMatch) => void;
}) {
  const [matches, setMatches] = useState<UpcomingMatch[] | null>(null);

  useEffect(() => {
    let alive = true;
    fetchUpcoming()
      .then((res) => alive && setMatches(res.matches))
      .catch(() => alive && setMatches([]));
    return () => {
      alive = false;
    };
  }, []);

  const shown = (matches ?? []).slice(0, 8);

  return (
    <section id="proximos" className="space-y-4 scroll-mt-20">
      <div className="flex items-end justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <span className="grid place-items-center h-9 w-9 rounded-xl bg-accent/15 text-accent">
            <Flame size={18} />
          </span>
          <div>
            <h2 className="text-lg font-bold text-white">Próximos partidos</h2>
            <p className="text-xs text-muted-2">
              Los enfrentamientos más relevantes de la agenda
            </p>
          </div>
        </div>
      </div>

      {matches === null ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="rounded-2xl border border-border bg-surface p-4 h-32 animate-pulse"
            />
          ))}
        </div>
      ) : shown.length === 0 ? (
        <div className="rounded-2xl border border-border bg-surface p-10 text-center text-sm text-muted-2">
          No hay partidos programados. Busca un partido manualmente arriba.
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
          {shown.map((m, i) => (
            <MatchCard key={i} match={m} onSelect={() => onSelectMatch(m)} />
          ))}
        </div>
      )}
    </section>
  );
}
