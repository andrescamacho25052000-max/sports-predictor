"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Star, Newspaper } from "lucide-react";
import { sidebarNav, followedLeagues } from "./nav";
import { cn } from "@/lib/utils";

/**
 * Sidebar izquierdo fijo (desktop) del layout Statix.
 * Contiene la navegación principal, las ligas seguidas y una tarjeta de noticias.
 */
export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden lg:flex flex-col fixed top-16 bottom-0 left-0 w-64 border-r border-border bg-background/80 backdrop-blur px-3 py-5 overflow-y-auto z-30">
      <p className="eyebrow px-3 mb-2">Navegación</p>
      <nav className="space-y-1">
        {sidebarNav.map((item) => {
          const active =
            item.href === "/" ? pathname === "/" : pathname?.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.label}
              href={item.href}
              className={cn(
                "relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-colors",
                active
                  ? "bg-white/[0.06] text-white font-semibold"
                  : "text-muted hover:text-white hover:bg-white/[0.03]"
              )}
            >
              {active && (
                <span className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-0.5 rounded-full bg-accent" />
              )}
              <Icon size={18} className={active ? "text-accent" : ""} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="flex items-center justify-between px-3 mt-6 mb-2">
        <p className="eyebrow">Ligas seguidas</p>
        <Star size={13} className="text-muted-2" />
      </div>
      <ul className="space-y-0.5">
        {followedLeagues.map((l) => (
          <li key={l.code}>
            <button className="w-full flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-muted hover:text-white hover:bg-white/[0.03] transition-colors">
              <span className="font-mono text-[10px] uppercase text-muted-2 w-7 text-left">
                {l.code}
              </span>
              <span className="flex-1 text-left truncate">{l.name}</span>
              <span className="font-mono text-[10px] text-muted-2 bg-white/5 rounded px-1.5 py-0.5">
                {l.count}
              </span>
            </button>
          </li>
        ))}
      </ul>

      <div className="mt-auto pt-4">
        <div className="flex items-center gap-2 rounded-xl border border-border bg-surface px-3 py-3 text-sm text-white">
          <Newspaper size={16} className="text-accent" />
          Noticias
        </div>
      </div>
    </aside>
  );
}
