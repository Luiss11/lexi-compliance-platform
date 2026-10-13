import { redirect } from "next/navigation";
import { getSession } from "@/lib/session";
import { AskForm } from "./AskForm";

export default async function AsistentePage() {
  const me = await getSession();
  if (!me) redirect("/logout");
  const isManager = me.user.role === "ADMIN" || me.user.role === "COMPLIANCE";

  return (
    <div className="flex max-w-3xl flex-col gap-6">
      <header>
        <h1 className="font-serif text-3xl font-semibold">Asistente legal</h1>
        <p className="mt-1 text-sm text-muted">
          Pregunta sobre los documentos de tu organización. Cada respuesta cita la página y la
          cláusula de donde sale.
        </p>
      </header>

      <div
        role="note"
        className="rounded-md border border-[#E3D3A6] bg-[#FFF8E6] px-4 py-3 text-sm text-[#5C4500]"
      >
        <strong>Aviso:</strong> Lexi es una herramienta de apoyo y no sustituye la asesoría de un
        abogado. Las respuestas se basan únicamente en los documentos que cargó tu organización.
      </div>

      <AskForm showScore={isManager} />
    </div>
  );
}
