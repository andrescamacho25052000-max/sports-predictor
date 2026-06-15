"use client";

import { useState, useRef } from "react";
import { Upload, Loader2, AlertTriangle, CheckCircle2, XCircle, Scale } from "lucide-react";
import { analyzeBetSlip, BetSlipAnalysis } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function BetSlipAnalyzer() {
  const [preview, setPreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<BetSlipAnalysis | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleFile(file: File) {
    setError("");
    setResult(null);
    if (!file.type.startsWith("image/")) {
      setError("Sube una imagen (captura del cupón).");
      return;
    }
    const dataUrl = await new Promise<string>((res, rej) => {
      const r = new FileReader();
      r.onload = () => res(r.result as string);
      r.onerror = rej;
      r.readAsDataURL(file);
    });
    setPreview(dataUrl);

    const base64 = dataUrl.split(",")[1];
    const mediaType = file.type;
    setLoading(true);
    try {
      const analysis = await analyzeBetSlip(base64, mediaType);
      setResult(analysis);
    } catch (e: unknown) {
      const detail =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail || "No se pudo analizar el cupón. Intenta con otra captura.");
    } finally {
      setLoading(false);
    }
  }

  const valueColor =
    result?.value === "positivo" ? "text-emerald-400"
    : result?.value === "justo" ? "text-amber-400"
    : "text-rose-400";

  return (
    <div className="space-y-4">
      <p className="text-gray-400 text-sm">
        Sube la captura de tu combinada y la herramienta lee cada pata y la evalúa
        contra el modelo: probabilidad, cuota mínima para tener valor, y veredicto.
      </p>

      {/* Zona de carga */}
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          const f = e.dataTransfer.files?.[0];
          if (f) handleFile(f);
        }}
        className="border-2 border-dashed border-white/15 hover:border-emerald-500/40 rounded-2xl p-6 text-center cursor-pointer transition-colors bg-white/5"
      >
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
        />
        {preview ? (
          <img src={preview} alt="cupón" className="max-h-48 mx-auto rounded-lg" />
        ) : (
          <div className="flex flex-col items-center gap-2 text-gray-400">
            <Upload className="w-7 h-7" />
            <span className="text-sm">Toca para subir o arrastra la captura del cupón</span>
          </div>
        )}
      </div>

      {loading && (
        <div className="flex items-center justify-center gap-2 text-emerald-400 text-sm py-3">
          <Loader2 className="w-4 h-4 animate-spin" />
          Leyendo el cupón y corriendo las predicciones…
        </div>
      )}

      {error && (
        <div className="bg-rose-500/10 border border-rose-500/30 rounded-xl p-3 flex items-start gap-2 text-rose-300 text-sm">
          <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {result && (
        <div className="space-y-3">
          {/* Patas */}
          <div className="space-y-2">
            {result.legs.map((leg, i) => {
              const high = leg.prob >= 70;
              const mid = leg.prob >= 55 && !high;
              return (
                <div key={i} className={cn(
                  "rounded-xl p-3 border flex items-center gap-3",
                  high ? "bg-emerald-500/5 border-emerald-500/25"
                  : mid ? "bg-white/5 border-amber-500/20"
                  : "bg-white/5 border-white/10"
                )}>
                  <span className="text-white/40 text-xs w-4 flex-shrink-0">{i + 1}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-white text-sm font-medium truncate">{leg.market}</p>
                    <p className="text-gray-500 text-xs truncate">{leg.match}</p>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <p className={cn("text-sm font-bold", high ? "text-emerald-400" : mid ? "text-amber-400" : "text-gray-300")}>
                      {leg.prob.toFixed(1)}%
                    </p>
                    <p className="text-gray-600 text-[10px]">&gt; {leg.min_odds.toFixed(2)}</p>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Resumen */}
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <p className={cn("text-2xl font-black leading-none", valueColor)}>
                  {result.combined_prob.toFixed(1)}%
                </p>
                <p className="text-gray-500 text-xs mt-1">prob. de ganar la combinada</p>
              </div>
              <div className="text-right">
                <p className="text-white text-2xl font-black leading-none">
                  &gt; {result.fair_odds.toFixed(2)}
                </p>
                <p className="text-gray-500 text-xs mt-1">
                  cuota justa{result.offered_odds ? ` · paga ${result.offered_odds.toFixed(2)}` : ""}
                </p>
              </div>
            </div>

            <div className={cn(
              "rounded-xl px-3 py-2 flex items-center gap-2 text-sm font-semibold",
              result.value === "positivo" ? "bg-emerald-500/10 text-emerald-300"
              : result.value === "justo" ? "bg-amber-500/10 text-amber-300"
              : "bg-rose-500/10 text-rose-300"
            )}>
              {result.value === "positivo" ? <CheckCircle2 className="w-4 h-4" />
               : result.value === "justo" ? <Scale className="w-4 h-4" />
               : <XCircle className="w-4 h-4" />}
              Valor {result.value}
            </div>

            <p className="text-gray-300 text-sm leading-relaxed">{result.verdict}</p>
            {result.weakest_leg && (
              <p className="text-gray-500 text-xs">Pata más débil: {result.weakest_leg}</p>
            )}
          </div>

          <p className="text-gray-600 text-[11px] leading-relaxed">
            Probabilidades estimadas por el modelo, no garantías. La cuota justa = 100 / probabilidad
            combinada; si Betplay paga menos, la combinada tiene valor esperado negativo.
          </p>
        </div>
      )}
    </div>
  );
}
