"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { mobileNav } from "./nav";
import { cn } from "@/lib/utils";

/** Navegación inferior tipo app (solo mobile) del layout Statix. */
export default function BottomNav() {
  const pathname = usePathname();

  return (
    <nav className="lg:hidden fixed bottom-0 inset-x-0 z-40 border-t border-border bg-background/95 backdrop-blur flex">
      {mobileNav.map((item) => {
        const active =
          item.href === "/" ? pathname === "/" : pathname?.startsWith(item.href);
        const Icon = item.icon;
        return (
          <Link
            key={item.label}
            href={item.href}
            className={cn(
              "flex-1 flex flex-col items-center gap-1 py-2.5 transition-colors",
              active ? "text-accent" : "text-muted-2 hover:text-white"
            )}
          >
            <Icon size={20} />
            <span className="text-[11px]">{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
