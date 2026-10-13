export interface EvidenceItem {
  id: string;
  task_id: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
  sha256: string;
  ai_verdict: string | null;
  uploaded_by_name: string | null;
  created_at: string;
}

export const VERDICT_LABEL: Record<string, string> = {
  NOT_REVIEWED: "Sin revisión automática",
  VALID: "Válida",
  INCOMPLETE: "Incompleta",
  INVALID: "No válida",
};

export function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
