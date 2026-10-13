import { NextResponse } from "next/server";
import { API_URL, getToken } from "@/lib/session";

// Sirve el archivo de una evidencia con la sesión del usuario: el navegador no puede
// llamar a la API directamente porque el token vive en una cookie HttpOnly.
export async function GET(req: Request, { params }: { params: { id: string; evidenceId: string } }) {
  const token = getToken();
  if (!token) return NextResponse.redirect(new URL("/logout", req.url));

  let res: Response;
  try {
    res = await fetch(`${API_URL}/evidence/${encodeURIComponent(params.evidenceId)}/file`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
  } catch {
    return new NextResponse("No se pudo conectar con el servidor.", { status: 502 });
  }

  if (res.status === 401) return NextResponse.redirect(new URL("/logout", req.url));
  if (!res.ok) {
    return new NextResponse("Archivo no disponible.", { status: res.status === 404 ? 404 : 502 });
  }

  return new NextResponse(res.body, {
    headers: {
      "Content-Type": res.headers.get("content-type") ?? "application/octet-stream",
      "Content-Disposition": res.headers.get("content-disposition") ?? "inline",
      "Cache-Control": "private, no-store",
      "X-Content-Type-Options": "nosniff",
    },
  });
}
