"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { X, Lock, KeyRound } from "lucide-react";
import { useAuth } from "@/lib/auth";

interface Props {
  onClose: () => void;
}

/** Modal para que el usuario autenticado cambie su contraseña. */
export default function ChangePasswordModal({ onClose }: Props) {
  const { changePassword } = useAuth();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (password.length < 6) {
      setError("La contraseña debe tener al menos 6 caracteres.");
      return;
    }
    if (password !== confirm) {
      setError("Las contraseñas no coinciden.");
      return;
    }
    setLoading(true);
    const res = await changePassword(password);
    setLoading(false);
    if (res.error) {
      setError(res.error);
      return;
    }
    setDone(true);
    setTimeout(onClose, 1500);
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

        <h3 className="text-lg font-bold text-white mb-1 flex items-center gap-2">
          <KeyRound size={18} className="text-emerald-400" />
          Cambiar contraseña
        </h3>
        <p className="text-sm text-white/50 mb-5">Mínimo 6 caracteres.</p>

        {done ? (
          <p className="text-emerald-400 text-sm py-4 text-center">✓ Contraseña actualizada.</p>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-3">
            <div className="flex items-center gap-2 bg-white/5 border border-white/10 rounded-lg px-3 py-2 focus-within:border-emerald-500">
              <Lock size={16} className="text-white/40 flex-shrink-0" />
              <input
                type="password"
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Nueva contraseña"
                className="w-full bg-transparent text-white text-sm focus:outline-none placeholder:text-white/30"
              />
            </div>
            <div className="flex items-center gap-2 bg-white/5 border border-white/10 rounded-lg px-3 py-2 focus-within:border-emerald-500">
              <Lock size={16} className="text-white/40 flex-shrink-0" />
              <input
                type="password"
                autoComplete="new-password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                placeholder="Repite la nueva contraseña"
                className="w-full bg-transparent text-white text-sm focus:outline-none placeholder:text-white/30"
              />
            </div>

            {error && <p className="text-red-400 text-sm">{error}</p>}

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-medium transition-colors disabled:opacity-50"
            >
              <KeyRound size={16} />
              {loading ? "Guardando..." : "Cambiar contraseña"}
            </button>
          </form>
        )}
      </motion.div>
    </div>
  );
}
