"use client";

interface RecentMatch {
  opponent: string;
  goals_for: number;
  goals_against: number;
  result: "V" | "E" | "D";
  was_home: boolean;
  date: string;
}

interface TeamData {
  ranking: number;
  league: string;
  recent_matches: RecentMatch[];
}

interface Props {
  home: TeamData;
  away: TeamData;
  homeTeam: string;
  awayTeam: string;
}

const resultStyle = {
  V: "bg-emerald-500 text-white",
  E: "bg-gray-500 text-white",
  D: "bg-red-500 text-white",
};

const resultLabel = { V: "V", E: "E", D: "D" };

function formatDate(dateStr: string) {
  if (!dateStr) return "";
  const [year, month, day] = dateStr.split("-");
  return `${day}/${month}/${year}`;
}

function RankingBadge({ ranking, league }: { ranking: number; league: string }) {
  const leagueExplained: Record<string, string> = {
    "Premier League":   "Liga de fútbol profesional de Inglaterra — 20 equipos",
    "La Liga":          "Liga de fútbol profesional de España — 20 equipos",
    "Bundesliga":       "Liga de fútbol profesional de Alemania — 18 equipos",
    "Serie A":          "Liga de fútbol profesional de Italia — 20 equipos",
    "Ligue 1":          "Liga de fútbol profesional de Francia — 18 equipos",
    "Champions League": "Torneo europeo de clubes — eliminatoria por fases",
  };

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="flex items-center gap-2">
        <span className="text-3xl font-black text-white">#{ranking}</span>
        <span className="text-xs text-gray-400 font-medium leading-tight max-w-[80px]">{league}</span>
      </div>
      <p className="text-gray-500 text-xs text-center leading-tight">
        {leagueExplained[league] || `Posición en ${league}`}
      </p>
    </div>
  );
}

function MatchRow({ match }: { match: RecentMatch }) {
  return (
    <div className="flex items-center gap-2 py-1.5 border-b border-white/5 last:border-0">
      {/* Resultado */}
      <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-black flex-shrink-0 ${resultStyle[match.result]}`}>
        {resultLabel[match.result]}
      </span>

      {/* Local/Visita */}
      <span className="text-gray-500 text-xs flex-shrink-0 w-8">
        {match.was_home ? "Casa" : "Vis."}
      </span>

      {/* Rival */}
      <span className="text-gray-300 text-xs flex-1 truncate">{match.opponent}</span>

      {/* Marcador */}
      <span className="text-white font-bold text-xs flex-shrink-0">
        {match.goals_for}–{match.goals_against}
      </span>

      {/* Fecha */}
      <span className="text-gray-600 text-xs flex-shrink-0">{formatDate(match.date)}</span>
    </div>
  );
}

function TeamColumn({ data, name }: { data: TeamData; name: string }) {
  return (
    <div className="flex-1 min-w-0 space-y-4">
      {/* Nombre del equipo */}
      <h4 className="text-white font-bold text-sm truncate">{name}</h4>

      {/* Ranking */}
      <div className="bg-white/5 rounded-xl p-3 border border-white/10">
        <p className="text-gray-400 text-xs mb-2 font-medium">Posición actual</p>
        <RankingBadge ranking={data.ranking} league={data.league} />
      </div>

      {/* Últimos partidos */}
      <div className="bg-white/5 rounded-xl p-3 border border-white/10">
        <p className="text-gray-400 text-xs mb-2 font-medium">Últimos 5 partidos</p>

        {/* Resumen visual */}
        <div className="flex gap-1 mb-3">
          {data.recent_matches.map((m, i) => (
            <span
              key={i}
              className={`flex-1 h-2 rounded-full ${
                m.result === "V" ? "bg-emerald-500" :
                m.result === "E" ? "bg-gray-500" : "bg-red-500"
              }`}
              title={`${m.result} vs ${m.opponent}`}
            />
          ))}
          {data.recent_matches.length === 0 && (
            <span className="text-gray-500 text-xs">Sin datos</span>
          )}
        </div>

        {/* Detalle partido a partido */}
        <div>
          {data.recent_matches.length > 0 ? (
            data.recent_matches.map((m, i) => <MatchRow key={i} match={m} />)
          ) : (
            <p className="text-gray-500 text-xs">No hay partidos disponibles</p>
          )}
        </div>
      </div>
    </div>
  );
}

export default function TeamStats({ home, away, homeTeam, awayTeam }: Props) {
  return (
    <div className="bg-white/5 border border-white/10 rounded-2xl p-5 space-y-3">
      <h3 className="text-lg font-semibold text-white">Estadísticas por equipo</h3>

      {/* Leyenda */}
      <div className="flex gap-3 text-xs">
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full bg-emerald-500 inline-block" /> Victoria
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full bg-gray-500 inline-block" /> Empate
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full bg-red-500 inline-block" /> Derrota
        </span>
      </div>

      {/* Columnas lado a lado */}
      <div className="flex gap-4">
        <TeamColumn data={home} name={homeTeam} />
        <div className="w-px bg-white/10 flex-shrink-0" />
        <TeamColumn data={away} name={awayTeam} />
      </div>
    </div>
  );
}
