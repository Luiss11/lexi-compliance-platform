"use server";

import { redirect } from "next/navigation";
import { API_URL, getToken } from "@/lib/session";
import type { QueryResponse } from "@/types/rag";

export interface AskState {
  question: string;
  result: QueryResponse | null;
  error: string | null;
}

export async function askAction(_prev: AskState, formData: FormData): Promise<AskState> {
  const question = String(formData.get("question") ?? "").trim();
  if (question.length < 3) {
    return { question, result: null, error: "Escribe tu pregunta (mínimo 3 caracteres)." };
  }
  if (question.length > 2000) {
    return { question, result: null, error: "La pregunta es demasiado larga (máximo 2000 caracteres)." };
  }

  const token = getToken();
  if (!token) redirect("/logout");

  let res: Response;
  try {
    res = await fetch(`${API_URL}/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ question }),
      cache: "no-store",
    });
  } catch {
    return { question, result: null, error: "No se pudo conectar con el servidor. Intenta de nuevo en un momento." };
  }

  if (res.status === 401) redirect("/logout");
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    return { question, result: null, error: body?.error?.message ?? "No se pudo obtener la respuesta." };
  }
  return { question, result: (await res.json()) as QueryResponse, error: null };
}
