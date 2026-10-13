"use server";

import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { API_URL, getToken } from "@/lib/session";

const MAX_BYTES = 20 * 1024 * 1024;

function back(params: { error?: string; ok?: string }): never {
  const q = new URLSearchParams(params as Record<string, string>).toString();
  redirect(`/documentos?${q}`);
}

async function call(path: string, init: RequestInit): Promise<Response> {
  const token = getToken();
  if (!token) redirect("/logout");
  try {
    return await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
  } catch {
    return back({ error: "No se pudo conectar con el servidor. Intenta de nuevo en un momento." });
  }
}

async function errorMessage(res: Response): Promise<string> {
  const body = await res.json().catch(() => null);
  return body?.error?.message ?? "No se pudo completar la acción.";
}

export async function uploadDocumentAction(formData: FormData): Promise<void> {
  const file = formData.get("file");
  const category = String(formData.get("category") ?? "").trim();
  const title = String(formData.get("title") ?? "").trim();

  if (!(file instanceof File) || file.size === 0) back({ error: "Elige un archivo PDF." });
  const pdf = file as File;
  if (pdf.size > MAX_BYTES) back({ error: "El PDF supera el límite de 20 MB." });
  if (!category) back({ error: "Elige una categoría." });

  const body = new FormData();
  body.set("file", pdf, pdf.name);
  body.set("category", category);
  if (title) body.set("title", title);

  const res = await call("/documents", { method: "POST", body });
  if (res.status === 401) redirect("/logout");
  if (!res.ok) back({ error: await errorMessage(res) });

  const doc = await res.json();
  revalidatePath("/documentos");
  back({ ok: `«${doc.title}» se guardó y quedó sellado con SHA-256.` });
}

export async function reindexDocumentAction(formData: FormData): Promise<void> {
  const id = String(formData.get("id") ?? "");
  if (!id) back({ error: "Documento no válido." });

  const res = await call(`/documents/${encodeURIComponent(id)}/index`, { method: "POST" });
  if (res.status === 401) redirect("/logout");
  if (!res.ok) back({ error: await errorMessage(res) });

  revalidatePath("/documentos");
  back({ ok: "Indexación completada." });
}
