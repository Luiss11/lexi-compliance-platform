import type { Role } from "@/lib/rbac";

export interface ManagedUser {
  id: string;
  full_name: string;
  email: string;
  role: Role;
  active: boolean;
}

export const ROLE_OPTIONS: { value: Role; label: string; help: string }[] = [
  { value: "ADMIN", label: "Administrador", help: "Gestiona usuarios y todo el sistema" },
  { value: "COMPLIANCE", label: "Oficial de cumplimiento", help: "Aprueba tareas, documentos y reportes" },
  { value: "OPERATOR", label: "Operador", help: "Trabaja sus tareas y sube evidencias" },
];

export const ROLE_NAME: Record<Role, string> = {
  ADMIN: "Administrador",
  COMPLIANCE: "Oficial de cumplimiento",
  OPERATOR: "Operador",
};
