import type { Role } from "@/lib/rbac";

export type TaskStatus = "BACKLOG" | "IN_PROGRESS" | "IN_REVIEW" | "DONE";
export type Priority = "ALTA" | "MEDIA" | "BAJA";

export interface Task {
  id: string;
  code: string;
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: Priority;
  due_date: string | null;
  assignee_id: string | null;
  assignee_name: string | null;
  document_id: string | null;
  citation: string | null;
  suggested_by_ai: boolean;
  overdue: boolean;
  created_at: string;
}

export interface Assignee {
  id: string;
  full_name: string;
  role: Role;
}

export const COLUMNS: { status: TaskStatus; label: string }[] = [
  { status: "BACKLOG", label: "Pendientes" },
  { status: "IN_PROGRESS", label: "En curso" },
  { status: "IN_REVIEW", label: "En revisión" },
  { status: "DONE", label: "Cumplidas" },
];

// Misma máquina de estados que el servicio de la API (la API es quien decide de verdad)
export const TRANSITIONS: Record<TaskStatus, TaskStatus[]> = {
  BACKLOG: ["IN_PROGRESS"],
  IN_PROGRESS: ["BACKLOG", "IN_REVIEW"],
  IN_REVIEW: ["IN_PROGRESS", "DONE"],
  DONE: ["IN_REVIEW"],
};

export const STATUS_LABEL: Record<TaskStatus, string> = {
  BACKLOG: "Pendientes",
  IN_PROGRESS: "En curso",
  IN_REVIEW: "En revisión",
  DONE: "Cumplidas",
};

export const PRIORITY_LABEL: Record<Priority, string> = {
  ALTA: "Alta",
  MEDIA: "Media",
  BAJA: "Baja",
};

/** Movimientos que el rol puede hacer desde un estado (el operador no cierra ni reabre). */
export function allowedMoves(from: TaskStatus, role: Role): TaskStatus[] {
  const moves = TRANSITIONS[from];
  if (role === "ADMIN" || role === "COMPLIANCE") return moves;
  if (from === "DONE") return [];
  return moves.filter((s) => s !== "DONE");
}
