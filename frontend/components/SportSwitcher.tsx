"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

/**
 * Selector de deporte: alterna entre Fútbol (/) y NBA (/nba).
 * Resalta el deporte activo según la ruta actual.
 */
export default function SportSwitcher() {
  const pathname = usePathname();
  const isNba = pathname?.startsWith("/nba");
  const base =
    "flex-1 flex items-center justify-center gap-1.5 px-4 py-2 rounded-lg text-sm font-bold transition-colors";

  return (
    <div className="flex gap-1 bg-white/5 border border-white/10 rounded-xl p-1 max-w-xs mx-auto">
      <Link
        href="/"
        className={cn(base, !isNba ? "bg-emerald-600 text-white shadow" : "text-white/50 hover:text-white")}
      >
        ⚽ Fútbol
      </Link>
      <Link
        href="/nba"
        className={cn(base, isNba ? "bg-orange-600 text-white shadow" : "text-white/50 hover:text-white")}
      >
        🏀 NBA
      </Link>
    </div>
  );
}
