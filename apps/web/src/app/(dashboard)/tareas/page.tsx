import Link from "next/link";
import { redirect } from "next/navigation";
import { API_URL, getSession, getToken } from "@/lib/session";
import {
  COLUMNS,
  PRIORITY_LABEL,
  STATUS_LABEL,
  allowedMoves,
  type Assignee,
  type Task,
} from "@/types/tasks";
import { createTaskAction, moveTaskAction } from "./actions";

async function api<T>(path: string): Promise<T | null> {
  const token = getToken();
  if (!token) redirect("/logout");
  try {
    const res = await fetch(`${API_URL}${path}`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    if (res.status === 401) redirect("/logout");
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

const PRIORITY_STYLE = {
  ALTA: "bg-[#FBE9E7] text-[#9A2D20]",
  MEDIA: "bg-[#FFF3D6] text-[#7A5600]",
  BAJA: "bg-[#E6F1EF] text-lexi",
} as const;

function formatDate(iso: string) {
  const [y, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}/${y}`;
}

export default async function TareasPage({
  searchParams,
}: {
  searchParams: { error?: string };
}) {
  const me = await getSession();
  if (!me) redirect("/logout");
  const role = me.user.role;
  const isManager = role === "ADMIN" || role === "COMPLIANCE";

  const [list, people] = await Promise.all([
    api<{ items: Task[] }>("/tasks"),
    isManager ? api<{ items: Assignee[] }>("/tasks/assignees") : Promise.resolve(null),
  ]);
  const tasks = list?.items ?? [];
  const assignees = people?.items ?? [];

  return (
    <div className="flex flex-col gap-6">
      <header>
        <h1 className="font-serif text-3xl font-semibold">Tareas</h1>
        <p className="mt-1 text-sm text-muted">
          {isManager
            ? "Obligaciones de cumplimiento de tu organización."
            : "Las tareas que tienes asignadas. Al terminar, pásalas a revisión."}
        </p>
      </header>

      {searchParams.error && (
        <div role="alert" className="rounded-md border border-[#E7B8B1] bg-[#FBE9E7] px-4 py-3 text-sm text-[#9A2D20]">
          {searchParams.error}
        </div>
      )}
      {list === null && (
        <div role="alert" className="rounded-md border border-line bg-white px-4 py-3 text-sm">
          No se pudieron cargar las tareas. Revisa que la API esté encendida.
        </div>
      )}

      {isManager && (
        <details className="rounded-lg border border-line bg-white p-4">
          <summary className="cursor-pointer text-sm font-medium">Nueva tarea</summary>
          <form action={createTaskAction} className="mt-4 grid gap-3 sm:grid-cols-2">
            <label className="flex flex-col gap-1 text-sm sm:col-span-2">
              Título
              <input name="title" required minLength={3} maxLength={200} className="min-h-11 rounded-md border border-line px-3" />
            </label>
            <label className="flex flex-col gap-1 text-sm sm:col-span-2">
              Descripción (opcional)
              <textarea name="description" rows={2} maxLength={2000} className="rounded-md border border-line px-3 py-2" />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              Prioridad
              <select name="priority" defaultValue="MEDIA" className="min-h-11 rounded-md border border-line px-3">
                <option value="ALTA">Alta</option>
                <option value="MEDIA">Media</option>
                <option value="BAJA">Baja</option>
              </select>
            </label>
            <label className="flex flex-col gap-1 text-sm">
              Fecha límite
              <input type="date" name="due_date" className="min-h-11 rounded-md border border-line px-3" />
            </label>
            <label className="flex flex-col gap-1 text-sm sm:col-span-2">
              Responsable
              <select name="assignee_id" defaultValue="" className="min-h-11 rounded-md border border-line px-3">
                <option value="">Sin asignar</option>
                {assignees.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.full_name}
                  </option>
                ))}
              </select>
            </label>
            <div className="sm:col-span-2">
              <button type="submit" className="min-h-11 rounded-md bg-lexi px-5 text-sm font-medium text-white">
                Crear tarea
              </button>
            </div>
          </form>
        </details>
      )}

      <section className="grid grid-cols-[repeat(auto-fit,minmax(240px,1fr))] gap-4">
        {COLUMNS.map((col) => {
          const items = tasks.filter((t) => t.status === col.status);
          return (
            <div key={col.status} className="flex flex-col gap-3 rounded-lg bg-[#ECEAE2] p-3">
              <h2 className="flex items-center justify-between px-1 text-sm font-semibold">
                {col.label}
                <span className="rounded-full bg-white px-2 text-xs font-normal">{items.length}</span>
              </h2>
              {items.length === 0 && <p className="px-1 text-sm text-muted">Sin tareas.</p>}
              {items.map((t) => (
                <article key={t.id} className="flex flex-col gap-2 rounded-md border border-line bg-white p-3">
                  <div className="flex items-center justify-between gap-2 text-xs text-muted">
                    <span className="font-mono">{t.code}</span>
                    <span className={`rounded px-2 py-0.5 font-medium ${PRIORITY_STYLE[t.priority]}`}>
                      {PRIORITY_LABEL[t.priority]}
                    </span>
                  </div>
                  <h3 className="text-sm font-medium">{t.title}</h3>
                  {t.citation && <p className="text-xs text-muted">{t.citation}</p>}
                  <div className="flex flex-wrap gap-x-3 text-xs text-muted">
                    <span>{t.assignee_name ?? "Sin asignar"}</span>
                    {t.due_date && (
                      <span className={t.overdue ? "font-medium text-[#9A2D20]" : ""}>
                        {t.overdue ? "Vencida · " : "Vence "}
                        {formatDate(t.due_date)}
                      </span>
                    )}
                  </div>
                  {t.status !== "BACKLOG" && (
                    <Link
                      href={`/tareas/${t.id}/evidencia`}
                      className="flex min-h-11 items-center text-xs font-medium text-lexi underline"
                    >
                      Evidencia ({t.evidence_count})
                    </Link>
                  )}
                  {t.status === "IN_PROGRESS" && t.evidence_count === 0 && (
                    <p className="text-xs text-muted">Sube una evidencia para enviarla a revisión.</p>
                  )}
                  <div className="flex flex-wrap gap-2">
                    {allowedMoves(t.status, role)
                      .filter((to) => !(t.status === "IN_PROGRESS" && to === "IN_REVIEW" && t.evidence_count === 0))
                      .map((to) => (
                        <form key={to} action={moveTaskAction}>
                          <input type="hidden" name="id" value={t.id} />
                          <input type="hidden" name="status" value={to} />
                          <button type="submit" className="min-h-11 rounded-md border border-line px-3 text-xs hover:bg-[#F5F4EF]">
                            Pasar a {STATUS_LABEL[to].toLowerCase()}
                          </button>
                        </form>
                      ))}
                  </div>
                </article>
              ))}
            </div>
          );
        })}
      </section>
    </div>
  );
}
