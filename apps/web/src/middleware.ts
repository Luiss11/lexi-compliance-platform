import { NextResponse, type NextRequest } from "next/server";
import { jwtVerify } from "jose";
import { canAccess, type Role } from "@/lib/rbac";

const COOKIE_NAME = "lexi_token";

async function readRole(req: NextRequest): Promise<Role | null> {
  const token = req.cookies.get(COOKIE_NAME)?.value;
  const rawSecret = process.env.JWT_SECRET;
  if (!token || !rawSecret) return null;
  try {
    const { payload } = await jwtVerify(token, new TextEncoder().encode(rawSecret));
    return (payload.role as Role) ?? null;
  } catch {
    return null; // token inválido o expirado
  }
}

function go(req: NextRequest, pathname: string) {
  const url = req.nextUrl.clone();
  url.pathname = pathname;
  url.search = "";
  return NextResponse.redirect(url);
}

export async function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;

  // /logout siempre pasa: es la salida cuando la sesión quedó inconsistente
  if (pathname.startsWith("/logout")) return NextResponse.next();

  const role = await readRole(req);

  if (pathname.startsWith("/login")) {
    return role ? go(req, "/panel") : NextResponse.next();
  }

  if (!role) return go(req, "/login");
  if (!canAccess(pathname, role)) return go(req, "/panel");
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next|favicon.ico|api/health).*)"],
};
