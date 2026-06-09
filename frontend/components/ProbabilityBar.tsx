"use client";

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { motion } from "framer-motion";

interface Props {
  homeTeam: string;
  awayTeam: string;
  homeWin: number;
  draw: number;
  awayWin: number;
  homeCrest?: string;
  awayCrest?: string;
}

const COLORS = ["#34d399", "#6b7280", "#818cf8"];

function TeamLogo({ crest, name, size }: { crest?: string; name: string; size: number }) {
  if (!crest) {
    return (
      <div
        className="rounded-full bg-white/10 flex items-center justify-center text-white font-black border border-white/20 text-base sm:text-lg flex-shrink-0"
        style={{ width: size, height: size }}
      >
        {name.slice(0, 2).toUpperCase()}
      </div>
    );
  }
  return (
    <img
      src={crest}
      alt={name}
      className="object-contain drop-shadow-lg flex-shrink-0"
      style={{ width: size, height: size }}
      onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
    />
  );
}

/* Nombre corto para mobile */
function shortName(name: string, max = 12) {
  if (name.length <= max) return name;
  // Última palabra (ej: "Atlético Nacional" → "Nacional")
  const parts = name.split(" ");
  return parts[parts.length - 1];
}

export default function ProbabilityBar({ homeTeam, awayTeam, homeWin, draw, awayWin, homeCrest, awayCrest }: Props) {
  const max = Math.max(homeWin, awayWin);
  const data = [
    { name: homeTeam, value: homeWin },
    { name: "Empate",  value: draw    },
    { name: awayTeam,  value: awayWin },
  ];

  const winner = homeWin === max ? homeTeam : awayWin === max ? awayTeam : "Empate";
  const winnerColor = homeWin === max ? "text-emerald-400" : awayWin === max ? "text-indigo-400" : "text-gray-400";

  return (
    <div className="space-y-5">
      <h3 className="text-base sm:text-lg font-semibold text-white text-center">Resultado estimado</h3>

      {/* Logos + dona */}
      <div className="flex items-center justify-between gap-2 sm:gap-4">

        {/* Local */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5 }}
          className="flex flex-col items-center gap-1.5 sm:gap-2 flex-1 min-w-0"
        >
          {/* Logo: 48px mobile, 56px desktop */}
          <TeamLogo crest={homeCrest} name={homeTeam} size={typeof window !== "undefined" && window.innerWidth < 640 ? 48 : 56} />
          <span className="text-white font-semibold text-xs sm:text-sm text-center leading-tight line-clamp-2 w-full">
            <span className="sm:hidden">{shortName(homeTeam)}</span>
            <span className="hidden sm:block">{homeTeam}</span>
          </span>
          <motion.span
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.3, type: "spring" }}
            className={`text-2xl sm:text-3xl font-black ${homeWin === max ? "text-emerald-400" : "text-white"}`}
          >
            {homeWin}%
          </motion.span>
          <span className="text-xs text-gray-500">Local</span>
        </motion.div>

        {/* Dona central */}
        <div className="flex flex-col items-center gap-1 flex-shrink-0">
          {/* 110px mobile, 144px desktop */}
          <div className="w-[110px] h-[110px] sm:w-36 sm:h-36 relative">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data}
                  cx="50%"
                  cy="50%"
                  innerRadius="60%"
                  outerRadius="88%"
                  dataKey="value"
                  startAngle={90}
                  endAngle={-270}
                  strokeWidth={0}
                >
                  {data.map((_, i) => (
                    <Cell key={i} fill={COLORS[i]} opacity={i === (homeWin === max ? 0 : awayWin === max ? 2 : 1) ? 1 : 0.55} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(v) => [`${v}%`]}
                  contentStyle={{ background: "#1f2937", border: "1px solid #374151", borderRadius: 12, color: "#fff", fontSize: 12 }}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
              <span className="text-gray-400 text-xs">Empate</span>
              <span className="text-white font-black text-base sm:text-lg">{draw}%</span>
            </div>
          </div>

          {/* Leyenda */}
          <div className="flex gap-2 sm:gap-3 mt-1">
            {[["#34d399", "L"], ["#6b7280", "E"], ["#818cf8", "V"]].map(([color, label]) => (
              <div key={label} className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full" style={{ background: color }} />
                <span className="text-xs text-gray-500">{label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Visitante */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5 }}
          className="flex flex-col items-center gap-1.5 sm:gap-2 flex-1 min-w-0"
        >
          <TeamLogo crest={awayCrest} name={awayTeam} size={typeof window !== "undefined" && window.innerWidth < 640 ? 48 : 56} />
          <span className="text-white font-semibold text-xs sm:text-sm text-center leading-tight line-clamp-2 w-full">
            <span className="sm:hidden">{shortName(awayTeam)}</span>
            <span className="hidden sm:block">{awayTeam}</span>
          </span>
          <motion.span
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.3, type: "spring" }}
            className={`text-2xl sm:text-3xl font-black ${awayWin === max ? "text-indigo-400" : "text-white"}`}
          >
            {awayWin}%
          </motion.span>
          <span className="text-xs text-gray-500">Visitante</span>
        </motion.div>
      </div>

      {/* Barra de probabilidad */}
      <div className="space-y-2">
        <div className="flex rounded-full overflow-hidden h-2.5 sm:h-3">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${homeWin}%` }}
            transition={{ duration: 0.8, ease: "easeOut" }}
            className="bg-emerald-500 h-full"
          />
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${draw}%` }}
            transition={{ duration: 0.8, ease: "easeOut", delay: 0.1 }}
            className="bg-gray-500 h-full"
          />
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${awayWin}%` }}
            transition={{ duration: 0.8, ease: "easeOut", delay: 0.2 }}
            className="bg-indigo-500 h-full"
          />
        </div>
        <p className="text-center text-xs text-gray-500">
          Pronóstico: <span className={`font-bold ${winnerColor}`}>{winner}</span>
        </p>
      </div>
    </div>
  );
}
