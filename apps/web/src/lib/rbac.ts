export type Role = "ADMIN" | "COMPLIANCE" | "OPERATOR";

// Qué rutas ve cada rol (TASK-13). La API vuelve a validar cada petición.
export const ROUTE_ACCESS: Record<string, Role[]> = {
  "/panel": ["ADMIN", "COMPLIANCE", "OPERATOR"],
  "/asistente": ["ADMIN", "COMPLIANCE", "OPERATOR"],
  "/documentos": ["ADMIN", "COMPLIANCE"],
  "/tareas": ["ADMIN", "COMPLIANCE", "OPERATOR"],
  "/evidencias": ["ADMIN", "COMPLIANCE", "OPERATOR"],
};

export function canAccess(pathname: string, role: Role): boolean {
  const base = "/" + (pathname.split("/")[1] ?? "");
  const allowed = ROUTE_ACCESS[base];
  return allowed ? allowed.includes(role) : true;
}
