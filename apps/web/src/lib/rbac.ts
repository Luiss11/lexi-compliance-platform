export type Role = "ADMIN" | "COMPLIANCE" | "OPERATOR";

export const ROUTE_ACCESS: Record<string, Role[]> = {
  "/panel": ["ADMIN", "COMPLIANCE", "OPERATOR"],
  "/asistente": ["ADMIN", "COMPLIANCE", "OPERATOR"],
  "/documentos": ["ADMIN", "COMPLIANCE"],
  "/tareas": ["ADMIN", "COMPLIANCE", "OPERATOR"],
  "/evidencias": ["ADMIN", "COMPLIANCE", "OPERATOR"],
  "/expediente": ["ADMIN", "COMPLIANCE"],
  "/auditoria": ["ADMIN", "COMPLIANCE"],
  "/vacios": ["ADMIN", "COMPLIANCE"],
};

export function canAccess(pathname: string, role: Role): boolean {
  const base = "/" + (pathname.split("/")[1] ?? "");
  const allowed = ROUTE_ACCESS[base];
  return allowed ? allowed.includes(role) : true;
}
