"use server";

import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { apiError, apiSend, NO_CONNECTION } from "@/lib/api";

export interface FormState {
  ok: string | null; // mensaje de éxito
  error: string | null;
}

async function finish(res: Response | null, okMessage: string): Promise<FormState> {
  if (!res) return { ok: null, error: NO_CONNECTION };
  if (res.status === 401) redirect("/logout");
  if (!res.ok) return { ok: null, error: await apiError(res) };
  revalidatePath("/usuarios");
  return { ok: okMessage, error: null };
}

export async function createUserAction(_prev: FormState, formData: FormData): Promise<FormState> {
  const res = await apiSend("POST", "/users", {
    full_name: String(formData.get("full_name") ?? ""),
    email: String(formData.get("email") ?? ""),
    role: String(formData.get("role") ?? "OPERATOR"),
    password: String(formData.get("password") ?? ""),
  });
  return finish(res, "Usuario creado. Entrégale su contraseña por un medio seguro y pídele cambiarla en «Mi cuenta».");
}

export async function updateUserAction(_prev: FormState, formData: FormData): Promise<FormState> {
  const id = String(formData.get("id") ?? "");
  const body: Record<string, unknown> = {};
  const role = formData.get("role");
  if (role) body.role = String(role);
  const active = formData.get("active");
  if (active !== null) body.active = String(active) === "true";
  const res = await apiSend("PATCH", `/users/${encodeURIComponent(id)}`, body);
  return finish(res, "Cambios guardados.");
}

export async function resetPasswordAction(_prev: FormState, formData: FormData): Promise<FormState> {
  const id = String(formData.get("id") ?? "");
  const res = await apiSend("POST", `/users/${encodeURIComponent(id)}/password`, {
    new_password: String(formData.get("new_password") ?? ""),
  });
  return finish(res, "Contraseña restablecida. Entrégasela por un medio seguro.");
}
