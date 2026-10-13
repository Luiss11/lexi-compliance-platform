// Solo para código de servidor (server components y server actions).
// No lo importes desde componentes "use client".
import { cookies } from "next/headers";
import type { Me } from "@/types/auth";

export const COOKIE_NAME = "lexi_token";

// Dentro de Docker la web llega a la API por el nombre del servicio (http://api:8000).
// Fuera de Docker cae a NEXT_PUBLIC_API_URL (http://localhost:8000).
export const API_URL =
  process.env.API_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export function getToken(): string | undefined {
  return cookies().get(COOKIE_NAME)?.value;
}

/** Usuario y organización de la sesión actual, o null si no hay sesión válida. */
export async function getSession(): Promise<Me | null> {
  const token = getToken();
  if (!token) return null;
  try {
    const res = await fetch(`${API_URL}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    if (!res.ok) return null;
    return (await res.json()) as Me;
  } catch {
    return null;
  }
}
