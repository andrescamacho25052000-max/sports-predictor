"use client";

interface Props {
  homeTeam: string;
  awayTeam: string;
  homeWin: number;
  draw: number;
  awayWin: number;
}

export default function ProbabilityBar({ homeTeam, awayTeam, homeWin, draw, awayWin }: Props) {
  const max = Math.max(homeWin, awayWin);

  return (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-white text-center">Resultado estimado</h3>

      {/* Visual bar */}
      <div className="flex rounded-full overflow-hidden h-8 text-xs font-bold">
        <div
          className="bg-emerald-500 flex items-center justify-center text-white transition-all duration-700"
          style={{ width: `${homeWin}%` }}
        >
          {homeWin}%
        </div>
        <div
          className="bg-gray-500 flex items-center justify-center text-white transition-all duration-700"
          style={{ width: `${draw}%` }}
        >
          {draw > 8 ? `${draw}%` : ""}
        </div>
        <div
          className="bg-blue-500 flex items-center justify-center text-white transition-all duration-700"
          style={{ width: `${awayWin}%` }}
        >
          {awayWin}%
        </div>
      </div>

      {/* Labels */}
      <div className="flex justify-between text-sm">
        <div className="flex flex-col items-start gap-1">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-emerald-500 inline-block" />
            <span className="text-gray-300 font-medium">{homeTeam}</span>
          </div>
          <span className={`text-2xl font-black ${homeWin === max ? "text-emerald-400" : "text-white"}`}>
            {homeWin}%
          </span>
        </div>

        <div className="flex flex-col items-center gap-1">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-gray-500 inline-block" />
            <span className="text-gray-300 font-medium">Empate</span>
          </div>
          <span className="text-2xl font-black text-white">{draw}%</span>
        </div>

        <div className="flex flex-col items-end gap-1">
          <div className="flex items-center gap-2">
            <span className="text-gray-300 font-medium">{awayTeam}</span>
            <span className="w-3 h-3 rounded-full bg-blue-500 inline-block" />
          </div>
          <span className={`text-2xl font-black ${awayWin === max ? "text-blue-400" : "text-white"}`}>
            {awayWin}%
          </span>
        </div>
      </div>
    </div>
  );
}
