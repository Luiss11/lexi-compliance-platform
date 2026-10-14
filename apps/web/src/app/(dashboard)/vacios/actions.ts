"use server";

import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { API_URL, getToken } from "@/lib/session";
import { citationOf, type GapAnalysis, type GapSuggestion } from "@/types/gaps";

export interface AnalyzeState {
  result: GapAnalysis | null;
  error: string | null;
}

export interface DismissState {
  dismissed: number | null;
  error: string | null;
}

export interface AcceptState {
  created: string[] | null; // códigos de las tareas creadas
  error: string | null;
}

async function post(path: string, body?: unknown): Promise<Response | null> {
  const token = getToken();
  if (!token) redirect("/logout");
  try {
    return await fetch(`${API_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: body === undefined ? undefined : JSON.stringify(body),
      cache: "no-store",
    });
  } catch {
    return null;
  }
}

async function errorMessage(res: Response): Promise<string> {
  const body = await res.json().catch(() => null);
  return body?.error?.message ?? "No se pudo completar la acción.";
}

export async function analyzeGapsAction(_prev: AnalyzeState, _formData: FormData): Promise<AnalyzeState> {
  const res = await post("/compliance/gaps/analyze");
  if (!res) return { result: null, error: "No se pudo conectar con el servidor. Intenta de nuevo en un momento." };
  if (res.status === 401) redirect("/logout");
  if (!res.ok) return { result: null, error: await errorMessage(res) };
  return { result: (await res.json()) as GapAnalysis, error: null };
}

export async function dismissGapsAction(_prev: DismissState, formData: FormData): Promise<DismissState> {
  const picked = new Set(formData.getAll("pick").map(String));
  let all: GapSuggestion[];
  try {
    all = JSON.parse(String(formData.get("payload") ?? "[]")) as GapSuggestion[];
  } catch {
    return { dismissed: null, error: "No se pudieron leer las sugerencias. Vuelve a analizar." };
  }
  const items = all
    .filter((s) => !picked.has(s.key))
    .map((s) => ({ document_id: s.document_id, page: s.page, clause: s.clause, title: s.title }));
  if (items.length === 0) return { dismissed: null, error: "No hay sugerencias sin marcar para descartar." };

  const res = await post("/compliance/gaps/dismiss", { items });
  if (!res) return { dismissed: null, error: "No se pudo conectar con el servidor. Intenta de nuevo en un momento." };
  if (res.status === 401) redirect("/logout");
  if (!res.ok) return { dismissed: null, error: await errorMessage(res) };
  return { dismissed: items.length, error: null };
}

export async function acceptGapsAction(_prev: AcceptState, formData: FormData): Promise<AcceptState> {
  const picked = new Set(formData.getAll("pick").map(String));
  if (picked.size === 0) return { created: null, error: "Elige al menos una sugerencia." };

  let all: GapSuggestion[];
  try {
    all = JSON.parse(String(formData.get("payload") ?? "[]")) as GapSuggestion[];
  } catch {
    return { created: null, error: "No se pudieron leer las sugerencias. Vuelve a analizar." };
  }

  const items = all
    .filter((s) => picked.has(s.key))
    .map((s) => ({
      title: s.title,
      description: `${s.description}\n\nFundamento: «${s.quote}»`.slice(0, 2000),
      priority: s.priority,
      due_date: s.due_date,
      document_id: s.document_id,
      citation: citationOf(s).slice(0, 300),
    }));
  if (items.length === 0) return { created: null, error: "Elige al menos una sugerencia." };

  const res = await post("/compliance/gaps/accept", { items });
  if (!res) return { created: null, error: "No se pudo conectar con el servidor. Intenta de nuevo en un momento." };
  if (res.status === 401) redirect("/logout");
  if (!res.ok) return { created: null, error: await errorMessage(res) };

  const body = (await res.json()) as { items: { code: string }[] };
  revalidatePath("/tareas");
  revalidatePath("/panel");
  return { created: body.items.map((t) => t.code), error: null };
}
