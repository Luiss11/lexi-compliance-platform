import { redirect } from "next/navigation";
import { API_URL, getToken } from "@/lib/session";
import { STATUS_LABEL, type TaskStatus } from "@/types/tasks";
import { formatSize } from "@/types/evidence";
import type { Dossier, Integrity } from "@/types/report";
import { PrintButton } from "./PrintButton";

async function loadDossier(): Promise<Dossier | null> {
  const token = getToken();
  if (!token) redirect("/logout");
  try {
    const res = await fetch(`${API_URL}/reports/dossier`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    if (res.status === 401) redirect("/logout");
    return res.ok ? ((await res.json()) as Dossier) : null;
  } catch {
    return null;
  }
}

const TZ = "America/Mexico_City";

function utc(iso: string) {
  return new Date(iso.endsWith("Z") ? iso : `${iso}Z`);
}
function dateTime(iso: string) {
  return utc(iso).toLocaleString("es-MX", { dateStyle: "long", timeStyle: "short", timeZone: TZ });
}
function dateShort(iso: string) {
  return utc(iso).toLocaleDateString("es-MX", { dateStyle: "short", timeZone: TZ });
}
function dueDate(iso: string) {
  const [y, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}/${y}`;
}

const INTEGRITY: Record<Integrity, { label: string; style: string }> = {
  OK: { label: "Íntegra", style: "bg-[#E6F1EF] text-[#1F6F5F]" },
  TAMPERED: { label: "ALTERADA", style: "bg-[#FBE9E7] text-[#9A2D20]" },
  MISSING: { label: "ARCHIVO FALTANTE", style: "bg-[#FBE9E7] text-[#9A2D20]" },
};

export default async function ExpedientePage() {
  const d = await loadDossier();

  if (!d) {
    return (
      <div role="alert" className="rounded-md border border-line bg-white px-4 py-3 text-sm">
        No se pudo generar el expediente. Revisa que la API esté encendida.
      </div>
    );
  }

  const clean = d.summary.integrity_failures === 0;
  const withoutEvidence = d.tasks.filter((t) => t.status === "DONE" && t.evidence.length === 0);

  return (
    <article className="mx-auto flex max-w-4xl flex-col gap-6 print:max-w-none print:gap-4 print:text-[11px]">
      <div className="flex flex-wrap items-center justify-between gap-3 print:hidden">
        <p className="text-sm text-muted">
          Foto del estado de cumplimiento al momento de abrir esta página. Cada evidencia se
          re-verifica contra su huella.
        </p>
        <div className="flex flex-wrap gap-2">
          <a
            href="/expediente/json"
            className="flex min-h-11 items-center rounded-md border border-line bg-white px-4 text-sm hover:bg-[#F5F4EF]"
          >
            Descargar JSON
          </a>
          <PrintButton />
        </div>
      </div>

      <header className="border-b border-line pb-4">
        <p className="text-[11px] tracking-widest text-muted">LEXI COMPLIANCE · EXPEDIENTE DE AUDITORÍA</p>
        <h1 className="mt-1 font-serif text-3xl font-semibold">{d.tenant_name}</h1>
        <p className="mt-1 text-sm text-muted">
          Generado el {dateTime(d.generated_at)}
          {d.generated_by ? ` por ${d.generated_by}` : ""}
        </p>
      </header>

      <section
        className={`rounded-lg border px-4 py-3 text-sm break-inside-avoid ${
          clean ? "border-[#B7D6D2] bg-[#E6F1EF] text-[#1F6F5F]" : "border-[#E7B8B1] bg-[#FBE9E7] text-[#9A2D20]"
        }`}
      >
        {d.summary.evidence_files === 0
          ? "Aún no hay evidencias registradas."
          : clean
            ? `Integridad verificada: las ${d.summary.evidence_files} evidencia(s) coinciden con su huella SHA-256 original.`
            : `ATENCIÓN: ${d.summary.integrity_failures} de ${d.summary.evidence_files} evidencia(s) no pasaron la verificación de integridad.`}
      </section>

      <section className="grid grid-cols-2 gap-3 sm:grid-cols-4 break-inside-avoid">
        {[
          ["Índice de cumplimiento", `${d.summary.score} · ${d.summary.score_label}`],
          ["Obligaciones cumplidas", `${d.summary.done} de ${d.summary.total_tasks}`],
          ["Vencidas", String(d.summary.overdue)],
          ["Evidencias selladas", String(d.summary.evidence_files)],
        ].map(([k, v]) => (
          <div key={k} className="rounded-lg border border-line bg-white p-3">
            <div className="text-xs text-muted">{k}</div>
            <div className="mt-1 font-serif text-xl font-semibold">{v}</div>
          </div>
        ))}
      </section>

      {withoutEvidence.length > 0 && (
        <section className="rounded-lg border border-[#E7B8B1] bg-[#FBE9E7] px-4 py-3 text-sm text-[#9A2D20] break-inside-avoid">
          <strong>Hallazgo:</strong> {withoutEvidence.map((t) => t.code).join(", ")} figura(n) como
          cumplida(s) sin evidencia sellada. Ante una auditoría no es posible demostrar su cumplimiento.
        </section>
      )}

      <section className="flex flex-col gap-3">
        <h2 className="font-serif text-xl font-semibold">Obligaciones y evidencias</h2>
        {d.tasks.length === 0 && <p className="text-sm text-muted">No hay obligaciones registradas.</p>}
        {d.tasks.map((t) => (
          <div key={t.code} className="rounded-lg border border-line bg-white p-4 break-inside-avoid">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <p className="font-mono text-xs text-muted">{t.code}</p>
                <h3 className="font-medium">{t.title}</h3>
              </div>
              <span className="rounded bg-[#ECEAE2] px-2 py-0.5 text-xs">{STATUS_LABEL[t.status as TaskStatus] ?? t.status}</span>
            </div>
            <p className="mt-1 text-xs text-muted">
              Prioridad {t.priority}
              {t.due_date ? ` · Vence ${dueDate(t.due_date)}` : ""}
              {t.overdue ? " (VENCIDA)" : ""}
              {t.assignee_name ? ` · Responsable: ${t.assignee_name}` : " · Sin responsable"}
            </p>
            {(t.citation || t.document_title) && (
              <p className="mt-1 text-xs text-muted">
                Fundamento: {[t.citation, t.document_title].filter(Boolean).join(" — ")}
              </p>
            )}

            {t.evidence.length === 0 ? (
              <p className="mt-3 text-xs italic text-muted">Sin evidencias.</p>
            ) : (
              <ul className="mt-3 flex flex-col gap-2">
                {t.evidence.map((e) => (
                  <li key={e.id} className="rounded-md border border-line px-3 py-2 break-inside-avoid">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="break-all text-sm">{e.filename}</span>
                      <span className={`rounded px-2 py-0.5 text-[11px] font-semibold ${INTEGRITY[e.integrity].style}`}>
                        {INTEGRITY[e.integrity].label}
                      </span>
                    </div>
                    <p className="mt-0.5 text-xs text-muted">
                      {formatSize(e.size_bytes)} · {dateShort(e.uploaded_at)}
                      {e.uploaded_by_name ? ` · ${e.uploaded_by_name}` : ""}
                    </p>
                    <p className="mt-0.5 break-all font-mono text-[10px] text-muted">SHA-256: {e.sha256}</p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </section>

      <section className="flex flex-col gap-3 break-inside-avoid">
        <h2 className="font-serif text-xl font-semibold">Base normativa</h2>
        {d.documents.length === 0 ? (
          <p className="text-sm text-muted">No hay documentos normativos cargados.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {d.documents.map((doc) => (
              <li key={doc.sha256} className="rounded-lg border border-line bg-white px-4 py-2 text-sm">
                <span className="font-medium">{doc.title}</span>{" "}
                <span className="text-xs text-muted">
                  · {doc.category}
                  {doc.pages ? ` · ${doc.pages} pág.` : ""} · {dateShort(doc.uploaded_at)}
                </span>
                <p className="break-all font-mono text-[10px] text-muted">SHA-256: {doc.sha256}</p>
              </li>
            ))}
          </ul>
        )}
      </section>

      <footer className="rounded-lg border border-line bg-white p-4 break-inside-avoid">
        <h2 className="text-sm font-semibold">Sello del expediente</h2>
        <p className="mt-1 break-all font-mono text-xs">{d.seal}</p>
        <p className="mt-2 text-xs leading-relaxed text-muted">
          Es el SHA-256 del contenido de este expediente (JSON con llaves ordenadas, sin espacios y
          sin el campo «seal»). Descarga el JSON y recalcula la huella: si algún dato cambió después
          de generarlo, el sello ya no coincidirá. Este documento no constituye asesoría legal.
        </p>
      </footer>
    </article>
  );
}
