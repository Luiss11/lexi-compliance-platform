"use server";

import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { API_URL, getToken } from "@/lib/session";
import type { TaskStatus } from "@/types/tasks";

const STATUSES: TaskStatus[] = ["BACKLOG", "IN_PROGRESS", "IN_REVIEW", "DONE"];

function fail(message: string): never {
  redirect(`/tareas?error=${encodeURIComponent(message)}`);
}

async function call(path: string, method: string, body: unknown): Promise<Response> {
  const token = getToken();
  if (!token) redirect("/logout");
  try {
    return await fetch(`${API_URL}${path}`, {
      method,
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
      cache: "no-store",
    });
  } catch {
    return fail("No se pudo conectar con el servidor. Intenta de nuevo en un momento.");
  }
}

async function errorMessage(res: Response): Promise<string> {
  const body = await res.json().catch(() => null);
  return body?.error?.message ?? "No se pudo completar la acción.";
}

export async function createTaskAction(formData: FormData): Promise<void> {
  const title = String(formData.get("title") ?? "").trim();
  const priority = String(formData.get("priority") ?? "MEDIA");
  const due = String(formData.get("due_date") ?? "");
  const assignee = String(formData.get("assignee_id") ?? "");
  const description = String(formData.get("description") ?? "").trim();

  if (title.length < 3) fail("El título debe tener al menos 3 caracteres.");

  const res = await call("/tasks", "POST", {
    title,
    priority,
    description: description || null,
    due_date: due || null,
    assignee_id: assignee || null,
  });
  if (res.status === 401) redirect("/logout");
  if (!res.ok) fail(await errorMessage(res));

  revalidatePath("/tareas");
  redirect("/tareas");
}

export async function moveTaskAction(formData: FormData): Promise<void> {
  const id = String(formData.get("id") ?? "");
  const status = String(formData.get("status") ?? "") as TaskStatus;
  if (!id || !STATUSES.includes(status)) fail("Movimiento no válido.");

  const res = await call(`/tasks/${encodeURIComponent(id)}/status`, "PATCH", { status });
  if (res.status === 401) redirect("/logout");
  if (!res.ok) fail(await errorMessage(res));

  revalidatePath("/tareas");
  redirect("/tareas");
}
