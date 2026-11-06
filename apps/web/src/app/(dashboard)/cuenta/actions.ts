"use server";

import { redirect } from "next/navigation";
import { apiError, apiSend, NO_CONNECTION } from "@/lib/api";

export interface PasswordState {
  ok: string | null;
  error: string | null;
}

export async function changePasswordAction(_prev: PasswordState, formData: FormData): Promise<PasswordState> {
  const next = String(formData.get("new_password") ?? "");
  if (next !== String(formData.get("confirm") ?? "")) {
    return { ok: null, error: "La confirmación no coincide con la nueva contraseña." };
  }
  const res = await apiSend("POST", "/auth/password", {
    current_password: String(formData.get("current_password") ?? ""),
    new_password: next,
  });
  if (!res) return { ok: null, error: NO_CONNECTION };
  if (res.status === 401) redirect("/logout");
  if (!res.ok) return { ok: null, error: await apiError(res) };
  return { ok: "Contraseña actualizada. Úsala la próxima vez que inicies sesión.", error: null };
}
