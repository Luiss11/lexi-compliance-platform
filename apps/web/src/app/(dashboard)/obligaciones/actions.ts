"use server";

import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { API_URL, getToken } from "@/lib/session";

export interface LoadState {
  created: string[] | null; // códigos de las tareas creadas
  skipped: number;
  error: string | null;
}

export async function loadObligationsAction(_prev: LoadState, formData: FormData): Promise<LoadState> {
  const ids = formData.getAll("pick").map(String);
  if (ids.length === 0) return { created: null, skipped: 0, error: "Elige al menos una obligación." };

  const token = getToken();
  if (!token) redirect("/logout");

  let res: Response;
  try {
    res = await fetch(`${API_URL}/compliance/obligations/load`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ ids }),
      cache: "no-store",
    });
  } catch {
    return { created: null, skipped: 0, error: "No se pudo conectar con el servidor. Intenta de nuevo en un momento." };
  }
  if (res.status === 401) redirect("/logout");
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    return { created: null, skipped: 0, error: body?.error?.message ?? "No se pudo cargar el catálogo." };
  }

  const body = (await res.json()) as { created: { code: string }[]; skipped: string[] };
  revalidatePath("/tareas");
  revalidatePath("/panel");
  revalidatePath("/obligaciones");
  return { created: body.created.map((t) => t.code), skipped: body.skipped.length, error: null };
}
