import {
  Home,
  CalendarDays,
  Sparkles,
  BarChart3,
  Trophy,
  User,
  MessageSquare,
  CircleUser,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
}

/** Navegación principal del sidebar (desktop). */
export const sidebarNav: NavItem[] = [
  { label: "Inicio", href: "/", icon: Home },
  { label: "Partidos", href: "/partidos", icon: CalendarDays },
  { label: "Predicciones", href: "/predicciones", icon: Sparkles },
  { label: "Estadísticas", href: "/track-record", icon: BarChart3 },
  { label: "Equipos", href: "/equipos", icon: Trophy },
  { label: "Jugadores", href: "/jugadores", icon: User },
  { label: "Comunidad", href: "/comunidad", icon: MessageSquare },
  { label: "Mi cuenta", href: "/cuenta", icon: CircleUser },
];

/** Navegación horizontal de la barra superior (desktop ancho). */
export const topNav: { label: string; href: string }[] = [
  { label: "Inicio", href: "/" },
  { label: "Fútbol", href: "/" },
  { label: "NBA", href: "/nba" },
  { label: "Ligas", href: "/ligas" },
  { label: "Equipos", href: "/equipos" },
  { label: "Jugadores", href: "/jugadores" },
  { label: "Partidos", href: "/partidos" },
  { label: "Predicciones", href: "/predicciones" },
  { label: "Estadísticas", href: "/track-record" },
  { label: "Comunidad", href: "/comunidad" },
];

/** Ligas seguidas (sidebar). Estático por ahora; se conectará al backend. */
export const followedLeagues: { code: string; name: string; count: number }[] = [
  { code: "ESP", name: "LaLiga", count: 12 },
  { code: "ENG", name: "Premier League", count: 10 },
  { code: "ITA", name: "Serie A", count: 10 },
  { code: "GER", name: "Bundesliga", count: 9 },
  { code: "FRA", name: "Ligue 1", count: 9 },
  { code: "UCL", name: "Champions League", count: 8 },
];

/** Navegación inferior (mobile). */
export const mobileNav: NavItem[] = [
  { label: "Inicio", href: "/", icon: Home },
  { label: "Partidos", href: "/partidos", icon: CalendarDays },
  { label: "IA", href: "/predicciones", icon: Sparkles },
  { label: "Stats", href: "/track-record", icon: BarChart3 },
  { label: "Perfil", href: "/cuenta", icon: CircleUser },
];
