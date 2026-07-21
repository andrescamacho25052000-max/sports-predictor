"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AnimatePresence } from "framer-motion";
import {
  Activity,
  Target,
  CheckCircle2,
  Clock,
  KeyRound,
  LogOut,
  Heart,
  Star,
  ChevronRight,
  type LucideIcon,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { fetchMyPredictions, PredictionRecord } from "@/lib/api";
import AuthModal from "@/components/AuthModal";
import ChangePasswordModal from "@/components/ChangePasswordModal";

function initials(email?: string | null): string {
  if (!email) return "TU";
  const name = email.split("@")[0];
  const parts = name.split(/[.\-_]/).filter(Boolean);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return name.slice(0, 2).toUpperCase();
}

function Kpi({
  label,
  value,
  icon: Icon,
  accent,
}: {
  label: string;
  value: string;
  icon: LucideIcon;
  accent?: boolean;
}) {
  return (
    <div className="rounded-2xl border border-border bg-surface p-4 sm:p-5">
      <div className="flex items-start justify-between gap-2">
        <p className="eyebrow">{label}</p>
        <span className="grid place-items-center h-8 w-8 rounded-lg bg-accent/15 text-accent shrink-0">
          <Icon size={16} />
        </span>
      </div>
      <p
        className={`mt-3 font-mono text-2xl sm:text-3xl font-bold tracking-tight ${
          accent ? "text-accent" : "text-white"
        }`}
      >
        {value}
      </p>
    </div>
  );
}

/** Placeholder honesto para módulos sin backend todavía (favoritos). */
function ComingSoonCard({
  title,
  icon: Icon,
}: {
  title: string;
  icon: LucideIcon;
}) {
  return (
    <section className="rounded-3xl border border-border bg-surface p-5 sm:p-6">
      <div className="flex items-center gap-2.5 mb-4">
        <Icon size={18} className="text-accent" />
        <h2 className="text-base font-bold text-white">{title}</h2>
      </div>
      <div className="rounded-2xl border border-dashed border-border bg-surface-2 px-4 py-8 text-center">
        <p className="text-sm text-muted">Próximamente</p>
        <p className="text-xs text-muted-2 mt-1">
          Podrás seguir tus equipos y jugadores favoritos aquí.
        </p>
      </div>
    </section>
  );
}

export default function CuentaPage() {
  const { user, session, loading, signOut } = useAuth();
  const [preds, setPreds] = useState<PredictionRecord[] | null>(null);
  const [showAuth, setShowAuth] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => {
    const token = session?.access_token;
    if (!token) return;
    let alive = true;
    fetchMyPredictions(token, 100)
      .then((r) => alive && setPreds(r.predictions))
      .catch(() => alive && setPreds([]));
    return () => {
      alive = false;
    };
  }, [session?.access_token]);

  // ── Sin sesión: puerta de acceso ──
  if (!loading && !session) {
    return (
      <div className="px-4 sm:px-6 py-10 max-w-7xl mx-auto">
        <div className="max-w-md mx-auto rounded-3xl border border-border bg-surface p-8 text-center space-y-4">
          <span className="inline-grid place-items-center h-14 w-14 rounded-2xl bg-accent/15 text-accent mx-auto">
            <KeyRound size={24} />
          </span>
          <h1 className="text-xl font-bold text-white">Inicia sesión</h1>
          <p className="text-sm text-muted">
            Entra para ver tu perfil, tus estadísticas y tu historial.
          </p>
          <button
            onClick={() => setShowAuth(true)}
            className="inline-flex items-center gap-1.5 rounded-xl bg-accent px-4 py-2.5 text-sm font-semibold text-black hover:bg-accent-strong transition-colors"
          >
            Entrar
          </button>
        </div>
        <AnimatePresence>
          {showAuth && <AuthModal onClose={() => setShowAuth(false)} />}
        </AnimatePresence>
      </div>
    );
  }

  const evaluated = (preds ?? []).filter((p) => p.result_actual != null).length;
  const correct = (preds ?? []).filter((p) => p.was_correct === true).length;
  const pending = (preds ?? []).length - evaluated;
  const accuracy = evaluated ? `${((correct / evaluated) * 100).toFixed(1)}%` : "—";
  const memberSince = user?.created_at
    ? new Date(user.created_at).getFullYear()
    : null;
  const emailName = user?.email?.split("@")[0] ?? "Tu cuenta";

  return (
    <div className="px-4 sm:px-6 py-6 space-y-6 max-w-7xl mx-auto">
      <div>
        <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-white">
          Mi cuenta
        </h1>
        <p className="text-sm text-muted-2 mt-1">
          Gestiona tu perfil y revisa tus estadísticas
        </p>
      </div>

      {/* Tarjeta de perfil */}
      <section className="relative overflow-hidden rounded-3xl border border-border bg-surface p-6 sm:p-8">
        <div className="pointer-events-none absolute -top-16 -right-10 h-48 w-48 rounded-full bg-accent/10 blur-3xl" />
        <div className="relative flex flex-col sm:flex-row sm:items-center gap-5">
          <span className="grid place-items-center h-20 w-20 rounded-full bg-accent/15 text-accent font-mono text-xl font-bold border border-accent/30 shrink-0">
            {initials(user?.email)}
          </span>
          <div className="min-w-0 flex-1">
            <h2 className="text-xl font-bold text-white truncate">{emailName}</h2>
            <p className="text-sm text-muted truncate">{user?.email}</p>
            {memberSince && (
              <p className="text-xs text-muted-2 mt-1">
                Miembro desde {memberSince}
              </p>
            )}
          </div>
          <div className="flex flex-wrap gap-2 shrink-0">
            <button
              onClick={() => setShowPassword(true)}
              className="inline-flex items-center gap-1.5 rounded-xl border border-border bg-surface-2 px-3.5 py-2 text-sm font-medium text-white hover:border-border-strong transition-colors"
            >
              <KeyRound size={15} />
              Cambiar contraseña
            </button>
            <button
              onClick={() => signOut()}
              className="inline-flex items-center gap-1.5 rounded-xl border border-border bg-surface-2 px-3.5 py-2 text-sm font-medium text-muted hover:text-white hover:border-border-strong transition-colors"
            >
              <LogOut size={15} />
              Salir
            </button>
          </div>
        </div>
      </section>

      {/* KPIs reales del usuario */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <Kpi label="Predicciones" value={preds ? String(preds.length) : "—"} icon={Activity} />
        <Kpi label="Acierto" value={accuracy} icon={Target} accent />
        <Kpi label="Evaluadas" value={preds ? String(evaluated) : "—"} icon={CheckCircle2} />
        <Kpi label="Pendientes" value={preds ? String(pending) : "—"} icon={Clock} />
      </div>

      {/* Últimas predicciones + Favoritos */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
        <section className="rounded-3xl border border-border bg-surface p-5 sm:p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-bold text-white">Mis últimas predicciones</h2>
            <Link
              href="/history"
              className="inline-flex items-center gap-1 text-xs font-medium text-accent"
            >
              Ver todas
              <ChevronRight size={14} />
            </Link>
          </div>
          {preds === null ? (
            <div className="space-y-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-12 rounded-xl bg-white/[0.04] animate-pulse" />
              ))}
            </div>
          ) : preds.length === 0 ? (
            <p className="text-sm text-muted-2 py-6 text-center">
              Aún no has generado predicciones.{" "}
              <Link href="/" className="text-accent">
                Analiza un partido
              </Link>
              .
            </p>
          ) : (
            <ul className="space-y-1.5">
              {preds.slice(0, 5).map((p) => {
                const state =
                  p.was_correct === true
                    ? { txt: "Acierto", cls: "text-accent" }
                    : p.was_correct === false
                    ? { txt: "Fallo", cls: "text-danger" }
                    : { txt: "Pendiente", cls: "text-muted-2" };
                return (
                  <li
                    key={p.id}
                    className="flex items-center justify-between gap-3 rounded-xl border border-border bg-surface-2 px-3 py-2.5"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-white truncate">
                        {p.home_team}{" "}
                        <span className="text-muted-2">vs</span> {p.away_team}
                      </p>
                      {p.league && (
                        <p className="text-[11px] text-muted-2 truncate">{p.league}</p>
                      )}
                    </div>
                    <span className={`text-xs font-semibold shrink-0 ${state.cls}`}>
                      {state.txt}
                    </span>
                  </li>
                );
              })}
            </ul>
          )}
        </section>

        <ComingSoonCard title="Equipos favoritos" icon={Heart} />
      </div>

      <ComingSoonCard title="Jugadores favoritos" icon={Star} />

      <AnimatePresence>
        {showPassword && (
          <ChangePasswordModal onClose={() => setShowPassword(false)} />
        )}
      </AnimatePresence>
    </div>
  );
}
