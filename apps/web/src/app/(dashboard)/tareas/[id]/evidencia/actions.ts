"use server";

import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { API_URL, getToken } from "@/lib/session";
import { VERDICT_LABEL } from "@/types/evidence";

const MAX_BYTES = 10 * 1024 * 1024;

function back(taskId: string, params: { error?: string; ok?: string }): never {
  const q = new URLSearchParams(params as Record<string, string>).toString();
  redirect(`/tareas/${encodeURIComponent(taskId)}/evidencia?${q}`);
}

async function call(taskId: string, path: string, init: RequestInit): Promise<Response> {
  const token = getToken();
  if (!token) redirect("/logout");
  try {
    return await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
  } catch {
    return back(taskId, { error: "No se pudo conectar con el servidor. Intenta de nuevo en un momento." });
  }
}

async function errorMessage(res: Response): Promise<string> {
  const body = await res.json().catch(() => null);
  return body?.error?.message ?? "No se pudo completar la acción.";
}

export async function uploadEvidenceAction(formData: FormData): Promise<void> {
  const taskId = String(formData.get("task_id") ?? "");
  const file = formData.get("file");
  if (!taskId) redirect("/tareas");

  if (!(file instanceof File) || file.size === 0) back(taskId, { error: "Elige una foto o un PDF." });
  const upload = file as File;
  if (upload.size > MAX_BYTES) back(taskId, { error: "La evidencia supera el límite de 10 MB." });

  const body = new FormData();
  body.set("evidence_file", upload, upload.name);

  const res = await call(taskId, `/tasks/${encodeURIComponent(taskId)}/evidence`, { method: "POST", body });
  if (res.status === 401) redirect("/logout");
  if (!res.ok) back(taskId, { error: await errorMessage(res) });

  const ev = await res.json();
  revalidatePath(`/tareas/${taskId}/evidencia`);
  revalidatePath("/tareas");
  const review =
    ev.ai_verdict && ev.ai_verdict !== "NOT_REVIEWED"
      ? ` Revisión con IA: ${VERDICT_LABEL[ev.ai_verdict] ?? ev.ai_verdict}${ev.ai_summary ? ` — ${ev.ai_summary}` : ""}`
      : "";
  back(taskId, { ok: `Evidencia sellada. Huella SHA-256: ${ev.sha256}.${review}` });
}

export async function verifyEvidenceAction(formData: FormData): Promise<void> {
  const taskId = String(formData.get("task_id") ?? "");
  const evidenceId = String(formData.get("evidence_id") ?? "");
  if (!taskId || !evidenceId) redirect("/tareas");

  const res = await call(taskId, `/evidence/${encodeURIComponent(evidenceId)}/verify`, { method: "POST" });
  if (res.status === 401) redirect("/logout");
  if (!res.ok) back(taskId, { error: await errorMessage(res) });

  const result = await res.json();
  if (result.tampered) {
    back(taskId, { error: "La evidencia fue alterada después de subirse: la huella ya no coincide." });
  }
  back(taskId, { ok: "Integridad verificada: la huella del archivo coincide con la original." });
}

export async function reviewEvidenceAction(formData: FormData): Promise<void> {
  const taskId = String(formData.get("task_id") ?? "");
  const evidenceId = String(formData.get("evidence_id") ?? "");
  if (!taskId || !evidenceId) redirect("/tareas");

  const res = await call(taskId, `/evidence/${encodeURIComponent(evidenceId)}/review`, { method: "POST" });
  if (res.status === 401) redirect("/logout");
  if (!res.ok) back(taskId, { error: await errorMessage(res) });

  const ev = await res.json();
  revalidatePath(`/tareas/${taskId}/evidencia`);
  revalidatePath("/panel");
  back(taskId, { ok: `Revisión con IA: ${VERDICT_LABEL[ev.ai_verdict] ?? ev.ai_verdict}.` });
}
