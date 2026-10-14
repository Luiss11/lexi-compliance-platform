import { GapsPanel } from "./GapsPanel";

export default function VaciosPage() {
  return (
    <div className="flex max-w-4xl flex-col gap-6">
      <header>
        <h1 className="font-serif text-3xl font-semibold">Vacíos normativos</h1>
        <p className="mt-2 text-sm text-muted">
          Obligaciones que tu normativa establece y que aún no tienen una tarea de cumplimiento. Solo se
          analizan documentos de tipo Ley, Norma oficial, Reglamento y Contrato; las políticas internas no.
        </p>
      </header>
      <GapsPanel />
      <p className="text-xs text-muted">
        Las propuestas son una ayuda para organizar tu cumplimiento y no constituyen asesoría legal.
        Confirma plazos y alcance con un profesional cuando aplique.
      </p>
    </div>
  );
}
