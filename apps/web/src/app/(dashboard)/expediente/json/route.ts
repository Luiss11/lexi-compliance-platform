import { NextResponse } from "next/server";
import { API_URL, getToken } from "@/lib/session";

// Descarga el expediente tal cual lo entrega la API (los mismos datos que sella),
// usando la cookie HttpOnly desde el servidor.
export async function GET(req: Request) {
  const token = getToken();
  if (!token) return NextResponse.redirect(new URL("/logout", req.url));

  let res: Response;
  try {
    res = await fetch(`${API_URL}/reports/dossier`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
  } catch {
    return new NextResponse("No se pudo conectar con el servidor.", { status: 502 });
  }

  if (res.status === 401) return NextResponse.redirect(new URL("/logout", req.url));
  if (!res.ok) return new NextResponse("No se pudo generar el expediente.", { status: res.status === 403 ? 403 : 502 });

  const stamp = new Date().toISOString().slice(0, 10);
  return new NextResponse(await res.text(), {
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Content-Disposition": `attachment; filename="expediente-lexi-${stamp}.json"`,
      "Cache-Control": "private, no-store",
      "X-Content-Type-Options": "nosniff",
    },
  });
}
