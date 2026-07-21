"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, Search, Bell } from "lucide-react";
import { topNav } from "./nav";
import { cn } from "@/lib/utils";
import AuthMenu from "@/components/AuthMenu";

/**
 * Barra superior fija del layout Statix: logo, navegación horizontal (desktop
 * ancho), búsqueda global (visual, la lógica ⌘K llega en una fase posterior),
 * notificaciones y menú de sesión.
 */
export default function TopBar() {
  const pathname = usePathname();

  return (
    <header className="fixed top-0 inset-x-0 h-16 z-40 border-b border-border bg-background/85 backdrop-blur">
      <div className="h-full flex items-center gap-3 px-4">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2.5 shrink-0">
          <span className="grid place-items-center h-9 w-9 rounded-xl bg-accent text-black shadow-[0_0_20px_-4px_var(--accent)]">
            <Activity size={20} strokeWidth={2.5} />
          </span>
          <span className="hidden sm:block leading-none">
            <span className="block font-bold text-white text-sm">Statix</span>
            <span className="block font-mono text-[9px] uppercase tracking-widest text-muted-2 mt-0.5">
              Sports Intelligence
            </span>
          </span>
        </Link>

        {/* Navegación horizontal (solo pantallas anchas) */}
        <nav className="hidden xl:flex items-center gap-0.5 mx-2">
          {topNav.map((item, i) => {
            const active =
              item.href === "/"
                ? pathname === "/"
                : pathname?.startsWith(item.href);
            return (
              <Link
                key={`${item.label}-${i}`}
                href={item.href}
                className={cn(
                  "px-3 py-1.5 rounded-lg text-sm transition-colors whitespace-nowrap",
                  active
                    ? "bg-white/[0.06] text-white font-medium"
                    : "text-muted hover:text-white"
                )}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* Búsqueda global + acciones (a la derecha) */}
        <div className="ml-auto flex items-center gap-2">
          <button
            type="button"
            className="hidden md:flex items-center gap-2 w-56 lg:w-72 rounded-xl border border-border bg-surface px-3 py-2 text-sm text-muted-2 hover:border-border-strong transition-colors"
            aria-label="Buscar equipos, jugadores, ligas o partidos"
          >
            <Search size={15} />
            <span className="flex-1 text-left truncate">
              Buscar equipos, jugadores...
            </span>
            <kbd className="font-mono text-[10px] text-muted-2 border border-border rounded px-1.5 py-0.5">
              ⌘K
            </kbd>
          </button>

          <button
            type="button"
            className="relative grid place-items-center h-9 w-9 rounded-xl border border-border text-muted hover:text-white transition-colors"
            aria-label="Notificaciones"
          >
            <Bell size={17} />
            <span className="absolute top-2 right-2 h-1.5 w-1.5 rounded-full bg-accent" />
          </button>

          <AuthMenu />
        </div>
      </div>
    </header>
  );
}
