"use server";

import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";
import { API_URL, COOKIE_NAME } from "@/lib/session";

export interface LoginState {
  error: string | null;
}

export async function loginAction(_prev: LoginState, formData: FormData): Promise<LoginState> {
  const tenant_slug = String(formData.get("tenant") ?? "").trim();
  const email = String(formData.get("email") ?? "").trim();
  const password = String(formData.get("password") ?? "");

  if (!tenant_slug || !email || !password) {
    return { error: "Completa organización, correo y contraseña." };
  }

  // La API ve siempre la IP de este servidor, no la del navegador. En producción Caddy pone
  // la IP real en X-Forwarded-For (e ignora la que mande el cliente); se la pasamos a la API
  // para que el freno de intentos fallidos por IP cuente a cada visitante por separado.
  const clientIp = headers().get("x-forwarded-for")?.split(",")[0]?.trim();

  let res: Response;
  try {
    res = await fetch(`${API_URL}/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(clientIp ? { "X-Forwarded-For": clientIp } : {}),
      },
      body: JSON.stringify({ tenant_slug, email, password }),
      cache: "no-store",
    });
  } catch {
    return { error: "No se pudo conectar con el servidor. Intenta de nuevo en un momento." };
  }

  if (!res.ok) {
    const body = await res.json().catch(() => null);
    return { error: body?.error?.message ?? "No se pudo iniciar sesión." };
  }

  const data = (await res.json()) as { access_token: string; expires_in: number };

  // HttpOnly: el JavaScript del navegador nunca puede leer el token
  cookies().set(COOKIE_NAME, data.access_token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: data.expires_in,
  });

  // redirect() lanza una excepción interna: va fuera de cualquier try/catch
  redirect("/panel");
}
