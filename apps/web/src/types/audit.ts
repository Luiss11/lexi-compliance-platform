export interface AuditEntry {
  id: string;
  action: string;
  entity_type: string;
  entity_id: string | null;
  actor_name: string | null;
  details: Record<string, unknown> | null;
  created_at: string;
}

export const ACTION_LABEL: Record<string, string> = {
  TASK_CREATED: "Tarea creada",
  TASK_UPDATED: "Tarea editada",
  TASK_STATUS_CHANGED: "Cambio de estado",
  EVIDENCE_UPLOADED: "Evidencia subida",
  EVIDENCE_VERIFIED: "Integridad verificada",
  EVIDENCE_TAMPERED: "Evidencia ALTERADA",
  EVIDENCE_REVIEWED: "Revisión con IA",
  DOCUMENT_UPLOADED: "Documento cargado",
  DOCUMENT_REINDEXED: "Documento reindexado",
  DOSSIER_GENERATED: "Expediente generado",
  GAPS_ANALYZED: "Análisis de vacíos",
  GAPS_DISMISSED: "Propuestas descartadas",
  TASK_DELETED: "Tarea eliminada",
};

const STATUS: Record<string, string> = {
  BACKLOG: "Pendiente",
  IN_PROGRESS: "En curso",
  IN_REVIEW: "En revisión",
  DONE: "Cumplida",
};
const VERDICT: Record<string, string> = { VALID: "válida", INCOMPLETE: "incompleta", INVALID: "no válida" };

function str(v: unknown): string {
  return typeof v === "string" ? v : "";
}

/** Texto corto en español con lo importante de cada evento. */
export function describe(a: { action: string; details: Record<string, unknown> | null }): string {
  const d = a.details ?? {};
  switch (a.action) {
    case "TASK_CREATED":
      return `${str(d.code)} · ${str(d.title)}${d.suggested_by_ai ? " · sugerida por IA" : ""}`;
    case "TASK_UPDATED":
      return `${str(d.code)} · campos: ${Array.isArray(d.fields) ? d.fields.join(", ") : ""}`;
    case "TASK_STATUS_CHANGED":
      return `${str(d.code)} · ${STATUS[str(d.from)] ?? str(d.from)} → ${STATUS[str(d.to)] ?? str(d.to)}`;
    case "EVIDENCE_UPLOADED":
      return `${str(d.task_code)} · ${str(d.filename)} · SHA-256 ${str(d.sha256).slice(0, 12)}…`;
    case "EVIDENCE_VERIFIED":
      return `${str(d.task_code)} · ${str(d.filename)} · coincide con su huella`;
    case "EVIDENCE_TAMPERED":
      return `${str(d.task_code)} · ${str(d.filename)} · ${str(d.state) === "MISSING" ? "archivo faltante" : "la huella ya no coincide"}`;
    case "EVIDENCE_REVIEWED":
      return `${str(d.task_code)} · ${str(d.filename)} · ${VERDICT[str(d.verdict)] ?? str(d.verdict)}`;
    case "DOCUMENT_UPLOADED":
    case "DOCUMENT_REINDEXED":
      return str(d.title);
    case "GAPS_DISMISSED":
      return Array.isArray(d.items) ? d.items.map((i) => str((i as Record<string, unknown>).title)).join(" · ") : "";
    case "TASK_DELETED":
      return `${str(d.code)} · ${str(d.title)}`;
    case "GAPS_ANALYZED":
      return `${d.suggestions ?? 0} propuesta(s) · ${d.passages ?? 0} fragmentos revisados`;
    case "DOSSIER_GENERATED":
      return `${d.tasks ?? 0} tareas · ${d.evidence_files ?? 0} evidencias · sello ${str(d.seal).slice(0, 12)}…`;
    default:
      return "";
  }
}
