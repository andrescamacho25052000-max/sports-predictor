"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Calendar, Globe, Flag, Building2, AlertTriangle, ChevronRight } from "lucide-react";
import { fetchUpcoming, UpcomingMatch, UpcomingResponse } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";

const NATIONAL_LEAGUES = new Set(["Mundial FIFA","Eurocopa","Copa América","Nations League"]);
const COLOMBIA_LEAGUES = new Set(["Liga BetPlay"]);

interface Props {
  onSelectMatch: (match: UpcomingMatch) => void;
  onLoaded?: (count: number) => void;
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return "";
  return new Date(dateStr).toLocaleDateString("es-ES", {
    weekday: "short", day: "2-digit", month: "short",
    hour: "2-digit", minute: "2-digit",
  });
}

function TeamBadge({ name, crest }: { name: string; crest?: string }) {
  return (
    <div className="flex flex-col items-center gap-1.5 flex-1 min-w-0">
      {crest ? (
        <img src={crest} alt={name}
          className="w-9 h-9 object-contain drop-shadow"
          onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
      ) : (
        <div className="w-9 h-9 rounded-full bg-white/10 border border-white/20 flex items-center justify-center text-xs font-black text-white">
          {name.slice(0, 2).toUpperCase()}
        </div>
      )}
      <span className="text-white text-xs font-semibold text-center leading-tight line-clamp-2 w-full">
        {name}
      </span>
    </div>
  );
}

function MatchCard({ match, onSelect, index }: { match: UpcomingMatch; onSelect: () => void; index: number }) {
  return (
    <motion.button
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.05 }}
      onClick={onSelect}
      className="group w-full text-left bg-white/5 hover:bg-white/10 border border-white/10 hover:border-emerald-500/50 rounded-2xl p-4 transition-all duration-200 space-y-3 cursor-pointer"
    >
      <div className="flex items-center justify-between">
        <span className="text-xs text-emerald-400 font-semibold truncate">{match.league}</span>
        <ChevronRight className="w-3.5 h-3.5 text-gray-600 group-hover:text-emerald-400 group-hover:translate-x-0.5 transition-all flex-shrink-0" />
      </div>

      <div className="flex items-center gap-2">
        <TeamBadge name={match.home} crest={match.home_crest} />
        <div className="flex-shrink-0 text-center">
          <span className="text-gray-600 text-xs font-bold">vs</span>
        </div>
        <TeamBadge name={match.away} crest={match.away_crest} />
      </div>

      <p className="text-gray-500 text-xs flex items-center gap-1">
        <Calendar className="w-3 h-3" />
        {formatDate(match.date)}
      </p>
    </motion.button>
  );
}

function SectionHeader({ icon: Icon, title, count }: { icon: React.ElementType; title: string; count: number }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <div className="p-1.5 bg-white/5 rounded-lg border border-white/10">
        <Icon className="w-4 h-4 text-emerald-400" />
      </div>
      <h3 className="text-sm font-bold text-gray-200">{title}</h3>
      <Badge variant="secondary">{count}</Badge>
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="bg-white/5 border border-white/10 rounded-2xl p-4 animate-pulse space-y-3">
      <div className="h-3 bg-white/10 rounded-full w-1/3" />
      <div className="flex gap-3 items-center">
        <div className="w-9 h-9 rounded-full bg-white/10 flex-shrink-0" />
        <div className="h-3 bg-white/10 rounded-full flex-1" />
        <div className="w-9 h-9 rounded-full bg-white/10 flex-shrink-0" />
      </div>
      <div className="h-3 bg-white/10 rounded-full w-1/2" />
    </div>
  );
}

export default function UpcomingMatches({ onSelectMatch, onLoaded }: Props) {
  const [matches,      setMatches]      = useState<UpcomingMatch[]>([]);
  const [betplayQuota, setBetplayQuota] = useState<UpcomingResponse["betplay_quota"] | null>(null);
  const [loading,      setLoading]      = useState(true);

  useEffect(() => {
    fetchUpcoming()
      .then(res => {
        setMatches(res.matches);
        setBetplayQuota(res.betplay_quota);
        onLoaded?.(res.matches.length);
      })
      .catch(() => onLoaded?.(0))
      .finally(() => setLoading(false));
  }, []);

  const nacional = matches.filter(m => NATIONAL_LEAGUES.has(m.league));
  const betplay  = matches.filter(m => COLOMBIA_LEAGUES.has(m.league));
  const clubes   = matches.filter(m => !NATIONAL_LEAGUES.has(m.league) && !COLOMBIA_LEAGUES.has(m.league));

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Calendar className="w-5 h-5 text-emerald-400" />
          <h2 className="text-lg font-bold text-white">Próximos Partidos</h2>
        </div>
        {!loading && (
          <Badge variant="secondary">{matches.length} partidos</Badge>
        )}
      </div>

      {/* Cuota BetPlay agotada */}
      {betplayQuota?.exhausted && (
        <div className="flex items-start gap-3 bg-yellow-500/10 border border-yellow-500/25 rounded-2xl px-4 py-3">
          <AlertTriangle className="w-4 h-4 text-yellow-400 mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-yellow-300 text-sm font-semibold">Liga BetPlay no disponible</p>
            <p className="text-yellow-500/80 text-xs mt-0.5">
              Se agotaron las 100 consultas diarias. Se mostrará mañana cuando se renueve el límite.
            </p>
          </div>
        </div>
      )}

      {/* Loading skeletons */}
      {loading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {[...Array(4)].map((_, i) => <SkeletonCard key={i} />)}
        </div>
      )}

      {/* Sin partidos */}
      {!loading && matches.length === 0 && (
        <div className="text-center py-10 space-y-2">
          <Calendar className="w-10 h-10 text-gray-700 mx-auto" />
          <p className="text-gray-400 text-sm">No hay partidos programados</p>
          <p className="text-gray-600 text-xs">Busca un partido manualmente arriba</p>
        </div>
      )}

      {/* Grid de secciones */}
      {!loading && matches.length > 0 && (
        <div className={`grid gap-6 items-start ${
          betplay.length > 0 ? "grid-cols-1 sm:grid-cols-3" : "grid-cols-1 sm:grid-cols-2"
        }`}>

          {nacional.length > 0 && (
            <div>
              <SectionHeader icon={Globe} title="Selecciones" count={nacional.length} />
              <div className="grid grid-cols-2 gap-3">
                {nacional.map((m, i) => (
                  <MatchCard key={i} match={m} onSelect={() => onSelectMatch(m)} index={i} />
                ))}
              </div>
            </div>
          )}

          {betplay.length > 0 && (
            <div>
              <SectionHeader icon={Flag} title="Colombia" count={betplay.length} />
              <div className="grid grid-cols-2 gap-3">
                {betplay.map((m, i) => (
                  <MatchCard key={i} match={m} onSelect={() => onSelectMatch(m)} index={i} />
                ))}
              </div>
            </div>
          )}

          {clubes.length > 0 && (
            <div>
              <SectionHeader icon={Building2} title="Clubes" count={clubes.length} />
              <div className="grid grid-cols-2 gap-3">
                {clubes.map((m, i) => (
                  <MatchCard key={i} match={m} onSelect={() => onSelectMatch(m)} index={i} />
                ))}
              </div>
            </div>
          )}

        </div>
      )}
    </div>
  );
}
