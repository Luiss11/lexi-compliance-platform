import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { API_URL, getSession, getToken } from "@/lib/session";
import { STATUS_LABEL, type Task } from "@/types/tasks";
import { VERDICT_LABEL, VERDICT_STYLE, formatSize, type EvidenceItem } from "@/types/evidence";
import { reviewEvidenceAction, uploadEvidenceAction, verifyEvidenceAction } from "./actions";

async function api<T>(path: string): Promise<{ status: number; data: T | null }> {
  const token = getToken();
  if (!token) redirect("/logout");
  try {
    const res = await fetch(`${API_URL}${path}`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    if (res.status === 401) redirect("/logout");
    return { status: res.status, data: res.ok ? ((await res.json()) as T) : null };
  } catch {
    return { status: 0, data: null };
  }
}

function formatDateTime(iso: string) {
  const d = new Date(iso.endsWith("Z") ? iso : `${iso}Z`);
  return d.toLocaleString("es-MX", { dateStyle: "short", timeStyle: "short", timeZone: "America/Mexico_City" });
}

export default async function EvidenciaPage({
  params,
  searchParams,
}: {
  params: { id: string };
  searchParams: { error?: string; ok?: string };
}) {
  const me = await getSession();
  if (!me) redirect("/logout");
  const isManager = me.user.role === "ADMIN" || me.user.role === "COMPLIANCE";

  const taskRes = await api<Task>(`/tasks/${encodeURIComponent(params.id)}`);
  if (taskRes.status === 404) notFound();
  const task = taskRes.data;
  const evRes = task ? await api<{ items: EvidenceItem[] }>(`/tasks/${encodeURIComponent(params.id)}/evidence`) : null;
  const items = evRes?.data?.items ?? [];
  const canUpload = task?.status === "IN_PROGRESS" || task?.status === "IN_REVIEW";

  return (
    <div className="flex max-w-3xl flex-col gap-6">
      <Link href="/tareas" className="flex min-h-11 items-center text-sm text-muted underline">
        ← Volver al tablero
      </Link>

      {!task ? (
        <div role="alert" className="rounded-md border border-line bg-white px-4 py-3 text-sm">
          No se pudo cargar la tarea. Revisa que la API esté encendida.
        </div>
      ) : (
        <header>
          <p className="font-mono text-xs text-muted">{task.code}</p>
          <h1 className="font-serif text-3xl font-semibold">{task.title}</h1>
          <p className="mt-1 text-sm text-muted">
            Estado: {STATUS_LABEL[task.status]}
            {task.citation ? ` · ${task.citation}` : ""}
          </p>
        </header>
      )}

      {searchParams.error && (
        <div role="alert" className="rounded-md border border-[#E7B8B1] bg-[#FBE9E7] px-4 py-3 text-sm text-[#9A2D20]">
          {searchParams.error}
        </div>
      )}
      {searchParams.ok && (
        <div role="status" className="break-all rounded-md border border-[#B7D6D2] bg-[#E6F1EF] px-4 py-3 text-sm text-lexi">
          {searchParams.ok}
        </div>
      )}

      {task && canUpload && (
        <form
          action={uploadEvidenceAction}
          encType="multipart/form-data"
          className="flex flex-col gap-3 rounded-lg border border-line bg-white p-4"
        >
          <h2 className="text-sm font-semibold">Subir evidencia</h2>
          <input type="hidden" name="task_id" value={task.id} />
          <label className="flex flex-col gap-1 text-sm">
            Foto o PDF (máximo 10 MB)
            <input
              type="file"
              name="file"
              accept="image/jpeg,image/png,application/pdf"
              capture="environment"
              required
              className="min-h-11 rounded-md border border-line px-3 py-2 text-sm"
            />
          </label>
          <p className="text-xs text-muted">
            Al subirla se calcula su huella SHA-256 y, si está activa, una revisión con IA te dice
            si parece completa. La evidencia no se puede editar ni reemplazar: una nueva subida
            crea un registro nuevo.
          </p>
          <div>
            <button type="submit" className="min-h-11 rounded-md bg-lexi px-5 text-sm font-medium text-white">
              Subir y sellar
            </button>
          </div>
        </form>
      )}
      {task && !canUpload && (
        <p className="rounded-md border border-line bg-white px-4 py-3 text-sm text-muted">
          {task.status === "DONE"
            ? "La tarea está cumplida: la evidencia ya no admite cambios."
            : "Pasa la tarea a «En curso» para poder subir evidencia."}
        </p>
      )}

      <section className="flex flex-col gap-3">
        <h2 className="text-sm font-semibold">
          Evidencias <span className="font-normal text-muted">({items.length})</span>
        </h2>
        {task && items.length === 0 && (
          <p className="rounded-lg border border-dashed border-line bg-white px-4 py-8 text-center text-sm text-muted">
            Aún no hay evidencias para esta tarea.
          </p>
        )}
        {items.map((e) => (
          <article key={e.id} className="flex flex-col gap-2 rounded-lg border border-line bg-white p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="break-all font-medium">{e.filename}</h3>
              <span
                className={`rounded px-2 py-0.5 text-xs ${VERDICT_STYLE[e.ai_verdict ?? "NOT_REVIEWED"] ?? VERDICT_STYLE.NOT_REVIEWED}`}
                title="La revisión con IA es una ayuda: no aprueba ni cierra la tarea"
              >
                IA: {VERDICT_LABEL[e.ai_verdict ?? "NOT_REVIEWED"] ?? e.ai_verdict}
              </span>
            </div>
            <p className="text-xs text-muted">
              {formatSize(e.size_bytes)} · {formatDateTime(e.created_at)}
              {e.uploaded_by_name ? ` · ${e.uploaded_by_name}` : ""}
            </p>
            {e.ai_summary && (
              <div className="rounded-md bg-[#F5F4EF] px-3 py-2 text-sm">
                <p>{e.ai_summary}</p>
                {e.ai_issues.length > 0 && (
                  <ul className="mt-1 list-disc pl-5 text-xs text-muted">
                    {e.ai_issues.map((issue) => (
                      <li key={issue}>{issue}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}
            <p className="break-all font-mono text-[11px] text-muted" title="Huella SHA-256 del archivo original">
              SHA-256: {e.sha256}
            </p>
            <div className="flex flex-wrap gap-2">
              <a
                href={`/tareas/${encodeURIComponent(params.id)}/evidencia/archivo/${encodeURIComponent(e.id)}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex min-h-11 items-center rounded-md border border-line px-3 text-xs hover:bg-[#F5F4EF]"
              >
                Ver archivo
              </a>
              <form action={reviewEvidenceAction}>
                <input type="hidden" name="task_id" value={params.id} />
                <input type="hidden" name="evidence_id" value={e.id} />
                <button type="submit" className="min-h-11 rounded-md border border-line px-3 text-xs hover:bg-[#F5F4EF]">
                  {e.ai_verdict && e.ai_verdict !== "NOT_REVIEWED" ? "Revisar de nuevo con IA" : "Revisar con IA"}
                </button>
              </form>
              {isManager && (
                <form action={verifyEvidenceAction}>
                  <input type="hidden" name="task_id" value={params.id} />
                  <input type="hidden" name="evidence_id" value={e.id} />
                  <button type="submit" className="min-h-11 rounded-md border border-line px-3 text-xs hover:bg-[#F5F4EF]">
                    Verificar integridad
                  </button>
                </form>
              )}
            </div>
          </article>
        ))}
      </section>
    </div>
  );
}
