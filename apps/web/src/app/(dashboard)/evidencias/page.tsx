import Link from "next/link";
import { redirect } from "next/navigation";
import { API_URL, getSession, getToken } from "@/lib/session";
import { STATUS_LABEL, type Task } from "@/types/tasks";

async function loadTasks(): Promise<Task[]> {
  const token = getToken();
  if (!token) redirect("/logout");
  try {
    const res = await fetch(`${API_URL}/tasks`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    if (res.status === 401) redirect("/logout");
    if (!res.ok) return [];
    return ((await res.json()) as { items: Task[] }).items;
  } catch {
    return [];
  }
}

export default async function EvidenciasPage() {
  const me = await getSession();
  if (!me) redirect("/logout");
  const tasks = (await loadTasks()).filter((t) => t.status !== "BACKLOG");

  return (
    <div className="flex flex-col gap-6">
      <header>
        <h1 className="font-serif text-3xl font-semibold">Evidencias</h1>
        <p className="mt-2 text-sm text-ink/70">
          Cada archivo se sella con SHA-256 al subirse. Elige una tarea para subir o revisar su
          evidencia.
        </p>
      </header>

      {tasks.length === 0 ? (
        <p className="rounded-lg border border-line bg-white p-6 text-sm text-ink/70">
          No hay tareas en curso. Mueve una tarea a &quot;En curso&quot; en el tablero para subir
          evidencia.
        </p>
      ) : (
        <ul className="flex flex-col gap-3">
          {tasks.map((t) => (
            <li
              key={t.id}
              className="flex items-center justify-between gap-4 rounded-lg border border-line bg-white p-4"
            >
              <div>
                <p className="text-xs text-ink/60">
                  {t.code} · {STATUS_LABEL[t.status]}
                </p>
                <p className="font-medium">{t.title}</p>
              </div>
              <Link
                href={`/tareas/${t.id}/evidencia`}
                className="shrink-0 rounded-md bg-lexi px-3 py-2 text-sm font-medium text-white"
              >
                Evidencia ({t.evidence_count})
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
