import { NextResponse, type NextRequest } from "next/server";
import { COOKIE_NAME } from "@/lib/session";

// Borra la cookie de sesión y manda a /login.
// En la interfaz se enlaza con un <a> normal (no <Link>) para que Next no lo precargue
// y cierre la sesión sin que nadie haya hecho clic.
export function GET(req: NextRequest) {
  const url = req.nextUrl.clone();
  url.pathname = "/login";
  url.search = "";
  const res = NextResponse.redirect(url);
  res.cookies.delete(COOKIE_NAME);
  return res;
}
