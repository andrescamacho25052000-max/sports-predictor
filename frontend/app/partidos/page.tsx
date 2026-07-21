"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence } from "framer-motion";
import { CalendarDays, ArrowUpRight } from "lucide-react";
import { fetchUpcoming, UpcomingMatch } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import AuthModal from "@/components/AuthModal";

type Filter = "todos" | "hoy" | "manana" | "semana";

const FILTERS: { key: Filter; label: string }[] = [
  { key: "todos", label: "Todos" },
  { key: "hoy", label: "Hoy" },
  { key: "manana", label: "Mañana" },
  { key: "semana", label: "Esta semana" },
];

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

export default function PartidosPage() {
  const router = useRouter();
  const { session } = useAuth();
  const [matches, setMatches] = useState<UpcomingMatch[] | null>(null);
  const [filter, setFilter] = useState<Filter>("todos");
  const [showAuth, setShowAuth] = useState(false);

  useEffect(() => {
    let alive = true;
    fetchUpcoming()
      .then((res) => alive && setMatches(res.matches))
      .catch(() => alive && setMatches([]));
    return () => {
      alive = false;
    };
  }, []);

  const filtered = useMemo(() => {
    if (!matches) return [];
    if (filter === "todos") return matches;
    const now = new Date();
    const startOfDay = (d: Date) =>
      new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
    const today = startOfDay(now);
    const day = 86_400_000;
    return matches.filter((m) => {
      if (!m.date) return false;
      const md = startOfDay(new Date(m.date));
      if (filter === "hoy") return md === today;
      if (filter === "manana") return md === today + day;
      if (filter === "semana") return md >= today && md < today + 7 * day;
      return true;
    });
  }, [matches, filter]);

  function goToMatch(m: UpcomingMatch) {
    if (!session) {
      setShowAuth(true);
      return;
    }
    const params = new URLSearchParams({
      home: m.home,
      away: m.away,
      league: m.league ?? "",
      date: m.date ?? "",
    });
    if (m.home_id) params.set("homeId", String(m.home_id));
    if (m.away_id) params.set("awayId", String(m.away_id));
    if (m.home_crest) params.set("homeCrest", m.home_crest);
    if (m.away_crest) params.set("awayCrest", m.away_crest);
    router.push(`/match?${params.toString()}`);
  }

  return (
    <div className="px-4 sm:px-6 py-6 max-w-7xl mx-auto space-y-6">
      <div>
        <p className="eyebrow text-accent">Calendario</p>
        <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-white mt-1">
          Partidos
        </h1>
        <p className="text-sm text-muted-2 mt-1 max-w-2xl">
          Explora los próximos partidos. Abre cualquiera para ver el análisis
          completo con probabilidades del modelo.
        </p>
      </div>

      {/* Filtros por fecha */}
      <div className="flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
              filter === f.key
                ? "bg-accent text-black"
                : "border border-border bg-surface text-muted hover:text-white"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {matches === null ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="rounded-2xl border border-border bg-surface h-32 animate-pulse"
            />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-2xl border border-border bg-surface p-10 text-center">
          <CalendarDays size={28} className="mx-auto text-muted-2 mb-2" />
          <p className="text-sm text-muted">
            No hay partidos para este filtro.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
          {filtered.map((m, i) => (
            <button
              key={i}
              onClick={() => goToMatch(m)}
              className="group text-left rounded-2xl border border-border bg-surface hover:border-border-strong p-4 transition-colors flex flex-col gap-3"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="eyebrow truncate">{m.league}</span>
                <span className="font-mono text-[10px] text-muted-2 shrink-0">
                  {formatDate(m.date)}
                </span>
              </div>
              <div className="space-y-2">
                <Team name={m.home} crest={m.home_crest} />
                <Team name={m.away} crest={m.away_crest} />
              </div>
              <div className="mt-auto flex items-center justify-end border-t border-border pt-2">
                <span className="inline-flex items-center gap-1 text-xs font-medium text-accent">
                  Ver análisis
                  <ArrowUpRight size={14} />
                </span>
              </div>
            </button>
          ))}
        </div>
      )}

      <AnimatePresence>
        {showAuth && <AuthModal onClose={() => setShowAuth(false)} />}
      </AnimatePresence>
    </div>
  );
}
