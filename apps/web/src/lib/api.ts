// Solo para código de servidor (server actions). Llamadas a la API con el token de la sesión.
import { redirect } from "next/navigation";
import { API_URL, getToken } from "@/lib/session";

/** Llama a la API; null si no hay conexión. Sin sesión, manda a /logout. */
export async function apiSend(method: "POST" | "PATCH", path: string, body?: unknown): Promise<Response | null> {
  const token = getToken();
  if (!token) redirect("/logout");
  try {
    return await fetch(`${API_URL}${path}`, {
      method,
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: body === undefined ? undefined : JSON.stringify(body),
      cache: "no-store",
    });
  } catch {
    return null;
  }
}

/** Mensaje en español para mostrar: el primer detalle de campo si existe, si no el mensaje general. */
export async function apiError(res: Response): Promise<string> {
  const body = await res.json().catch(() => null);
  const field = body?.error?.details?.fields?.[0]?.msg;
  return field ?? body?.error?.message ?? "No se pudo completar la acción.";
}

export const NO_CONNECTION = "No se pudo conectar con el servidor. Intenta de nuevo en un momento.";
