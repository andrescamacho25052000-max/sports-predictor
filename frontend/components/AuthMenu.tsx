"use client";

import { useState } from "react";
import { AnimatePresence } from "framer-motion";
import { LogIn, LogOut, User as UserIcon, KeyRound } from "lucide-react";
import { useAuth } from "@/lib/auth";
import AuthModal from "@/components/AuthModal";
import ChangePasswordModal from "@/components/ChangePasswordModal";

/**
 * Widget de autenticación para cabeceras.
 * Muestra un botón "Entrar" si no hay sesión, o el email + "Salir" si la hay.
 */
export default function AuthMenu() {
  const { user, loading, signOut } = useAuth();
  const [showModal, setShowModal] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  if (loading) {
    return <div className="h-8 w-20 rounded-full bg-white/5 animate-pulse" />;
  }

  if (user) {
    const label = user.email?.split("@")[0] ?? "Cuenta";
    return (
      <div className="flex items-center gap-2">
        <span className="flex items-center gap-1.5 text-xs text-white/60 bg-white/5 border border-white/10 rounded-full px-3 py-1.5 max-w-[140px]">
          <UserIcon size={13} className="text-emerald-400 flex-shrink-0" />
          <span className="truncate">{label}</span>
        </span>
        <button
          onClick={() => setShowPassword(true)}
          title="Cambiar contraseña"
          className="flex items-center text-xs text-white/50 hover:text-emerald-400 transition-colors border border-white/10 hover:border-emerald-500/30 rounded-full px-2.5 py-1.5"
        >
          <KeyRound size={13} />
        </button>
        <button
          onClick={() => signOut()}
          title="Cerrar sesión"
          className="flex items-center gap-1 text-xs text-white/50 hover:text-red-400 transition-colors border border-white/10 hover:border-red-500/30 rounded-full px-2.5 py-1.5"
        >
          <LogOut size={13} />
          <span className="hidden sm:inline">Salir</span>
        </button>
        <AnimatePresence>
          {showPassword && <ChangePasswordModal onClose={() => setShowPassword(false)} />}
        </AnimatePresence>
      </div>
    );
  }

  return (
    <>
      <button
        onClick={() => setShowModal(true)}
        className="flex items-center gap-1.5 text-xs font-medium text-emerald-400 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 rounded-full px-3 py-1.5 transition-colors"
      >
        <LogIn size={14} />
        Entrar
      </button>
      <AnimatePresence>
        {showModal && <AuthModal onClose={() => setShowModal(false)} />}
      </AnimatePresence>
    </>
  );
}
