"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { X, Mail, Lock, LogIn, UserPlus } from "lucide-react";
import { useAuth } from "@/lib/auth";

interface Props {
  onClose: () => void;
}

type Mode = "signin" | "signup";

/** Modal de inicio de sesión / registro con email y contraseña. */
export default function AuthModal({ onClose }: Props) {
  const { signIn, signUp } = useAuth();
  const [mode, setMode] = useState<Mode>("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setInfo("");
    if (!email || !password) {
      setError("Ingresa email y contraseña.");
      return;
    }
    setLoading(true);
    const res = mode === "signin"
      ? await signIn(email, password)
      : await signUp(email, password);
    setLoading(false);

    if (res.error) {
      setError(res.error);
      return;
    }
    if (mode === "signup" && res.needsConfirmation) {
      setInfo("Cuenta creada. Revisa tu email para confirmarla antes de entrar.");
      return;
    }
    onClose();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.9 }}
        className="bg-gray-900 border border-white/10 rounded-2xl p-6 w-full max-w-sm shadow-2xl relative"
      >
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-white/40 hover:text-white transition-colors"
          aria-label="Cerrar"
        >
          <X size={18} />
        </button>

        <h3 className="text-lg font-bold text-white mb-1">
          {mode === "signin" ? "Iniciar sesión" : "Crear cuenta"}
        </h3>
        <p className="text-sm text-white/50 mb-5">
          {mode === "signin"
            ? "Entra para guardar tu historial y preferencias."
            : "Regístrate para guardar tus análisis."}
        </p>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="flex items-center gap-2 bg-white/5 border border-white/10 rounded-lg px-3 py-2 focus-within:border-emerald-500">
            <Mail size={16} className="text-white/40 flex-shrink-0" />
            <input
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="tu@email.com"
              className="w-full bg-transparent text-white text-sm focus:outline-none placeholder:text-white/30"
            />
          </div>
          <div className="flex items-center gap-2 bg-white/5 border border-white/10 rounded-lg px-3 py-2 focus-within:border-emerald-500">
            <Lock size={16} className="text-white/40 flex-shrink-0" />
            <input
              type="password"
              autoComplete={mode === "signin" ? "current-password" : "new-password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Contraseña"
              className="w-full bg-transparent text-white text-sm focus:outline-none placeholder:text-white/30"
            />
          </div>

          {error && <p className="text-red-400 text-sm">{error}</p>}
          {info && <p className="text-emerald-400 text-sm">{info}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-medium transition-colors disabled:opacity-50"
          >
            {mode === "signin" ? <LogIn size={16} /> : <UserPlus size={16} />}
            {loading ? "Procesando..." : mode === "signin" ? "Entrar" : "Registrarme"}
          </button>
        </form>

        <button
          onClick={() => { setMode(mode === "signin" ? "signup" : "signin"); setError(""); setInfo(""); }}
          className="w-full text-center text-sm text-white/50 hover:text-emerald-400 transition-colors mt-4"
        >
          {mode === "signin"
            ? "¿No tienes cuenta? Regístrate"
            : "¿Ya tienes cuenta? Inicia sesión"}
        </button>
      </motion.div>
    </div>
  );
}
