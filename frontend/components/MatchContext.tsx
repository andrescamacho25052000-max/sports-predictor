"use client";

import { Stadium, Weather, InjuredPlayer } from "@/lib/api";

interface InjuriesData {
  home: { team: string; players: InjuredPlayer[] };
  away: { team: string; players: InjuredPlayer[] };
}

interface Props {
  stadium?: Stadium;
  weather?: Weather;
  injuries?: InjuriesData;
}

const surfaceLabel: Record<string, string> = {
  "grass":          "Césped natural",
  "artificial turf":"Césped artificial",
  "hybrid grass":   "Césped híbrido",
  "dirt":           "Tierra",
};

function InjurySection({ label, players }: { label: string; players: InjuredPlayer[] }) {
  return (
    <div className="flex-1 min-w-0">
      <p className="text-gray-400 text-xs font-medium mb-2">{label}</p>
      {players.length === 0 ? (
        <div className="flex items-center gap-2">
          <span className="text-emerald-400 text-sm">✓</span>
          <span className="text-gray-400 text-xs">Sin lesionados conocidos</span>
        </div>
      ) : (
        <ul className="space-y-1">
          {players.map((p, i) => (
            <li key={i} className="flex items-start gap-2">
              <span className="text-red-400 text-xs mt-0.5 flex-shrink-0">✕</span>
              <div>
                <p className="text-white text-xs font-medium leading-tight">{p.name}</p>
                <p className="text-gray-500 text-xs">{p.reason}</p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function MatchContext({ stadium, weather, injuries }: Props) {
  if (!stadium && !weather && !injuries) return null;

  return (
    <div className="space-y-4">

      {/* Estadio */}
      {stadium && (
        <div className="bg-white/5 border border-white/10 rounded-2xl p-5">
          <h3 className="text-lg font-semibold text-white mb-4">🏟️ Estadio</h3>
          <div className="flex gap-4 items-start">
            {stadium.image && (
              <img
                src={stadium.image}
                alt={stadium.name}
                className="w-24 h-16 object-cover rounded-lg flex-shrink-0 bg-white/10"
                onError={(e) => (e.currentTarget.style.display = "none")}
              />
            )}
            <div className="space-y-2 flex-1">
              <p className="text-white font-bold text-base">{stadium.name}</p>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                <div>
                  <span className="text-gray-500">Ciudad</span>
                  <p className="text-gray-200">{stadium.city}</p>
                </div>
                {stadium.capacity && (
                  <div>
                    <span className="text-gray-500">Capacidad</span>
                    <p className="text-gray-200">{stadium.capacity.toLocaleString()} personas</p>
                  </div>
                )}
                {stadium.surface && (
                  <div>
                    <span className="text-gray-500">Superficie</span>
                    <p className="text-gray-200">{surfaceLabel[stadium.surface] ?? stadium.surface}</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Clima */}
      {weather && (
        <div className="bg-white/5 border border-white/10 rounded-2xl p-5">
          <h3 className="text-lg font-semibold text-white mb-4">🌤️ Clima el día del partido</h3>
          <div className="flex items-center gap-5">
            <span className="text-5xl">{weather.emoji}</span>
            <div className="flex-1 space-y-1">
              <p className="text-white font-bold text-base">{weather.description}</p>
              <p className="text-gray-400 text-xs">{weather.city} · {weather.date}</p>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-3 mt-4">
            <div className="bg-white/5 rounded-xl p-3 text-center">
              <p className="text-gray-400 text-xs">Temperatura</p>
              <p className="text-white font-bold">{weather.temp_min}° – {weather.temp_max}°C</p>
            </div>
            <div className="bg-white/5 rounded-xl p-3 text-center">
              <p className="text-gray-400 text-xs">Lluvia</p>
              <p className="text-white font-bold">{weather.precipitation} mm</p>
            </div>
            <div className="bg-white/5 rounded-xl p-3 text-center">
              <p className="text-gray-400 text-xs">Viento</p>
              <p className="text-white font-bold">{weather.windspeed} km/h</p>
            </div>
          </div>
          <div className="mt-3 bg-yellow-500/10 border border-yellow-500/20 rounded-xl px-4 py-2">
            <p className="text-yellow-300 text-xs">⚽ {weather.impact}</p>
          </div>
        </div>
      )}

      {/* Lesiones */}
      {injuries && (
        <div className="bg-white/5 border border-white/10 rounded-2xl p-5">
          <h3 className="text-lg font-semibold text-white mb-4">🏥 Lesionados y sancionados</h3>
          <div className="flex gap-6">
            <InjurySection
              label={injuries.home.team}
              players={injuries.home.players}
            />
            <div className="w-px bg-white/10 flex-shrink-0" />
            <InjurySection
              label={injuries.away.team}
              players={injuries.away.players}
            />
          </div>
        </div>
      )}

    </div>
  );
}
