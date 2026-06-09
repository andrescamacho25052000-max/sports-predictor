"use client";

import { useState, useEffect, useRef } from "react";
import axios from "axios";

import { API_URL } from "@/lib/config";
const api = axios.create({ baseURL: API_URL });

interface TeamOption {
  id: number;
  name: string;
}

interface Props {
  onAnalyze: (payload: {
    home: string; away: string; league: string;
    home_id?: number; away_id?: number;
  }) => void;
}

function TeamInput({
  label,
  value,
  selectedId,
  onChange,
  onSelect,
  placeholder,
}: {
  label: string;
  value: string;
  selectedId: number | null;
  onChange: (v: string) => void;
  onSelect: (t: TeamOption) => void;
  placeholder: string;
}) {
  const [options, setOptions]   = useState<TeamOption[]>([]);
  const [open, setOpen]         = useState(false);
  const [loading, setLoading]   = useState(false);
  const timer  = useRef<ReturnType<typeof setTimeout> | null>(null);
  const wrapRef = useRef<HTMLDivElement>(null);

  // Cerrar dropdown al hacer click fuera
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // Buscar con debounce
  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);

    if (value.trim().length < 2) {
      setOptions([]);
      setOpen(false);
      return;
    }

    // Si ya hay un equipo seleccionado y el texto coincide, no buscar de nuevo
    if (selectedId !== null) return;

    timer.current = setTimeout(async () => {
      setLoading(true);
      try {
        const { data } = await api.get(`/teams/search?q=${encodeURIComponent(value.trim())}`);
        setOptions(data.teams ?? []);
        setOpen((data.teams ?? []).length > 0);
      } catch {
        setOptions([]);
      } finally {
        setLoading(false);
      }
    }, 300);

    return () => { if (timer.current) clearTimeout(timer.current); };
  }, [value, selectedId]);

  const confirmed = selectedId !== null;

  return (
    <div ref={wrapRef} className="relative space-y-1.5">
      <label className="text-sm text-gray-400 font-medium">{label}</label>

      <div className="relative">
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => options.length > 0 && !confirmed && setOpen(true)}
          placeholder={placeholder}
          className={`w-full bg-white/8 border rounded-xl px-4 py-3 pr-10 text-white placeholder-gray-600
            focus:outline-none focus:ring-2 transition-all text-sm
            ${confirmed
              ? "border-emerald-500/60 bg-emerald-500/8 focus:ring-emerald-500/40"
              : "border-white/15 focus:ring-emerald-500/40 focus:border-emerald-500/30 focus:bg-white/12"
            }`}
        />

        {/* Icono derecho: check si confirmado, spinner si buscando */}
        <div className="absolute inset-y-0 right-3 flex items-center pointer-events-none">
          {confirmed ? (
            <svg className="w-4 h-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7"/>
            </svg>
          ) : loading ? (
            <svg className="animate-spin w-4 h-4 text-gray-500" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
              <path className="opacity-80" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
            </svg>
          ) : null}
        </div>
      </div>

      {/* Dropdown de sugerencias */}
      {open && !confirmed && options.length > 0 && (
        <ul className="absolute z-50 w-full mt-1 bg-gray-900 border border-white/15 rounded-xl shadow-2xl overflow-hidden">
          {options.map((t) => (
            <li key={t.id}>
              <button
                type="button"
                onMouseDown={(e) => {
                  e.preventDefault();   // evitar que onBlur cierre antes
                  onSelect(t);
                  setOpen(false);
                }}
                className="w-full text-left px-4 py-2.5 text-sm text-gray-200 hover:bg-white/10 hover:text-white transition-colors flex items-center gap-2"
              >
                <span className="text-emerald-500 text-xs font-mono">#{t.id}</span>
                {t.name}
              </button>
            </li>
          ))}
        </ul>
      )}

      {/* Aviso si no hay resultados */}
      {open && !confirmed && options.length === 0 && !loading && value.trim().length >= 2 && (
        <p className="text-xs text-gray-600 pl-1">Sin resultados — prueba en inglés</p>
      )}
    </div>
  );
}


export default function CustomMatchForm({ onAnalyze }: Props) {
  const [homeName, setHomeName] = useState("");
  const [awayName, setAwayName] = useState("");
  const [homeId,   setHomeId]   = useState<number | null>(null);
  const [awayId,   setAwayId]   = useState<number | null>(null);

  const canAnalyze = homeName.trim().length >= 2 && awayName.trim().length >= 2
                     && homeName !== awayName;

  const bothResolved = homeId !== null && awayId !== null;

  function handleAnalyze() {
    if (!canAnalyze) return;
    onAnalyze({
      home:    homeName,
      away:    awayName,
      league:  "",
      home_id: homeId  ?? undefined,
      away_id: awayId  ?? undefined,
    });
  }

  return (
    <div className="space-y-5">

      <div className="space-y-1">
        <h2 className="text-base font-bold text-white">Partido personalizado</h2>
        <p className="text-xs text-gray-500">
          Escribe cualquier equipo. Si está en nuestra base de datos, el XGBoost
          usará sus datos reales.
        </p>
      </div>

      {/* Inputs de equipos */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <TeamInput
          label="Equipo local"
          value={homeName}
          selectedId={homeId}
          placeholder="ej. Bayern, Arsenal…"
          onChange={(v) => { setHomeName(v); setHomeId(null); }}
          onSelect={(t) => { setHomeName(t.name); setHomeId(t.id); }}
        />
        <TeamInput
          label="Equipo visitante"
          value={awayName}
          selectedId={awayId}
          placeholder="ej. Dortmund, Chelsea…"
          onChange={(v) => { setAwayName(v); setAwayId(null); }}
          onSelect={(t) => { setAwayName(t.name); setAwayId(t.id); }}
        />
      </div>

      {/* Indicador de estado */}
      {canAnalyze && (
        <div className={`text-xs px-3 py-2 rounded-lg flex items-center gap-2
          ${bothResolved
            ? "bg-emerald-500/10 border border-emerald-500/20 text-emerald-400"
            : "bg-yellow-500/10 border border-yellow-500/20 text-yellow-400"
          }`}>
          {bothResolved ? (
            <>
              <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7"/>
              </svg>
              Ambos equipos identificados — XGBoost usará datos reales + Elo
            </>
          ) : (
            <>
              <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
              {homeId === null && awayId === null
                ? "Selecciona ambos equipos del desplegable para máxima precisión"
                : homeId === null
                ? `Selecciona "${homeName}" del desplegable para máxima precisión`
                : `Selecciona "${awayName}" del desplegable para máxima precisión`}
            </>
          )}
        </div>
      )}

      <button
        onClick={handleAnalyze}
        disabled={!canAnalyze}
        className="w-full bg-emerald-500 hover:bg-emerald-400 disabled:bg-gray-700 disabled:cursor-not-allowed
          text-white font-bold py-3.5 rounded-xl transition-all duration-200 text-sm shadow-lg
          shadow-emerald-500/20 active:scale-95 flex items-center justify-center gap-2"
      >
        Analizar partido
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6"/>
        </svg>
      </button>
    </div>
  );
}
