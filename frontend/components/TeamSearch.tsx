"use client";

import { useState, useEffect, useRef } from "react";
import axios from "axios";
import { UpcomingMatch } from "@/lib/api";

import { API_URL } from "@/lib/config";
const api = axios.create({ baseURL: API_URL });

interface Props {
  onSelectMatch: (match: UpcomingMatch) => void;
  onQueryChange?: (q: string) => void;
}

function formatDate(d?: string) {
  if (!d) return "";
  return new Date(d).toLocaleDateString("es-ES", {
    weekday: "short", day: "2-digit", month: "short",
    hour: "2-digit", minute: "2-digit",
  });
}

/* Resalta la parte del nombre que coincide con la búsqueda */
function Highlight({ text, query }: { text: string; query: string }) {
  const idx = text.toLowerCase().indexOf(query.toLowerCase());
  if (idx === -1 || !query) return <span>{text}</span>;
  return (
    <span>
      {text.slice(0, idx)}
      <span className="text-emerald-400 font-bold">{text.slice(idx, idx + query.length)}</span>
      {text.slice(idx + query.length)}
    </span>
  );
}

export default function TeamSearch({ onSelectMatch, onQueryChange }: Props) {
  const [query,   setQuery]   = useState("");
  const [results, setResults] = useState<UpcomingMatch[]>([]);
  const [loading, setLoading] = useState(false);
  const [done,    setDone]    = useState(false);   // ¿ya se hizo al menos una búsqueda?
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    onQueryChange?.(query);

    if (query.trim().length < 2) {
      setResults([]);
      setDone(false);
      return;
    }

    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(async () => {
      setLoading(true);
      setDone(false);
      try {
        const { data } = await api.get(`/search?q=${encodeURIComponent(query.trim())}`);
        setResults(data.matches ?? []);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
        setDone(true);
      }
    }, 400);

    return () => { if (timer.current) clearTimeout(timer.current); };
  }, [query]);

  const clear = () => { setQuery(""); setResults([]); setDone(false); inputRef.current?.focus(); };

  return (
    <div className="space-y-3">

      {/* ── Barra de búsqueda ── */}
      <div className="relative">
        <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
          {loading ? (
            <svg className="animate-spin h-5 w-5 text-emerald-400" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
              <path className="opacity-80" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
            </svg>
          ) : (
            <svg className="h-5 w-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
            </svg>
          )}
        </div>

        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Busca un equipo o selección…"
          className="w-full bg-white/8 border border-white/15 rounded-2xl pl-12 pr-12 py-4 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/60 focus:border-emerald-500/40 focus:bg-white/12 transition-all text-base"
        />

        {query && (
          <button
            onClick={clear}
            className="absolute inset-y-0 right-4 flex items-center text-gray-500 hover:text-white transition"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        )}
      </div>

      {/* ── Sin resultados ── */}
      {done && !loading && results.length === 0 && (
        <div className="text-center py-8 space-y-1">
          <p className="text-gray-400 text-sm">No se encontraron partidos próximos para</p>
          <p className="text-white font-semibold">"{query}"</p>
          <p className="text-gray-600 text-xs pt-1">Prueba con el nombre en inglés o revisa la ortografía</p>
        </div>
      )}

      {/* ── Resultados ── */}
      {results.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs text-gray-500 pl-1">
            {results.length} partido{results.length !== 1 ? "s" : ""} encontrado{results.length !== 1 ? "s" : ""} para
            <span className="text-gray-300 font-medium"> "{query}"</span>
          </p>

          {results.map((match, i) => {
            const homeMatch = match.home.toLowerCase().includes(query.toLowerCase());
            const awayMatch = match.away.toLowerCase().includes(query.toLowerCase());
            return (
              <button
                key={i}
                onClick={() => onSelectMatch(match)}
                className="w-full group bg-white/5 border border-white/10 rounded-2xl p-4 text-left hover:bg-white/10 hover:border-emerald-500/40 transition-all flex items-center gap-4"
              >
                {/* info */}
                <div className="flex-1 min-w-0 space-y-1">
                  <span className="text-xs text-emerald-400/80 font-medium">{match.league}</span>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`text-sm font-semibold ${homeMatch ? "text-white" : "text-gray-400"}`}>
                      <Highlight text={match.home} query={query} />
                    </span>
                    <span className="text-gray-600 text-xs">vs</span>
                    <span className={`text-sm font-semibold ${awayMatch ? "text-white" : "text-gray-400"}`}>
                      <Highlight text={match.away} query={query} />
                    </span>
                  </div>
                  {match.date && (
                    <p className="text-gray-500 text-xs">{formatDate(match.date)}</p>
                  )}
                </div>

                {/* flecha */}
                <span className="flex-shrink-0 text-emerald-400 text-sm font-semibold group-hover:text-emerald-300 transition-colors flex items-center gap-1">
                  Analizar
                  <svg className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6"/>
                  </svg>
                </span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
