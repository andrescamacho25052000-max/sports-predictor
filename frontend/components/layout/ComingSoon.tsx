import { Sparkles } from "lucide-react";

/**
 * Pantalla placeholder para secciones aún no construidas, replicando la del
 * prototipo Statix ("Esta sección forma parte del rediseño...").
 */
export default function ComingSoon({ title }: { title: string }) {
  return (
    <div className="px-4 py-6 sm:py-8">
      <div className="max-w-6xl mx-auto rounded-3xl border border-border bg-gradient-to-br from-surface to-background min-h-[60vh] grid place-items-center text-center px-6">
        <div className="space-y-4 max-w-md">
          <span className="inline-grid place-items-center h-14 w-14 rounded-2xl bg-accent/15 text-accent">
            <Sparkles size={26} />
          </span>
          <h1 className="text-2xl font-bold text-white">{title}</h1>
          <p className="text-muted leading-relaxed">
            Esta sección forma parte del rediseño. Se construirá en la próxima
            fase con los datos de tu backend.
          </p>
        </div>
      </div>
    </div>
  );
}
