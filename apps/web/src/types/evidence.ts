export interface EvidenceItem {
  id: string;
  task_id: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
  sha256: string;
  ai_verdict: string | null;
  ai_summary: string | null;
  ai_issues: string[];
  uploaded_by_name: string | null;
  created_at: string;
}

export const VERDICT_LABEL: Record<string, string> = {
  NOT_REVIEWED: "Sin revisión automática",
  VALID: "Válida",
  INCOMPLETE: "Incompleta",
  INVALID: "No válida",
};

// Colores del veredicto de la IA (asesora, no decide)
export const VERDICT_STYLE: Record<string, string> = {
  NOT_REVIEWED: "bg-[#ECEAE2] text-[#4B4F58]",
  VALID: "bg-[#E6F1EF] text-[#1F6F5F]",
  INCOMPLETE: "bg-[#FFF3D6] text-[#7A5600]",
  INVALID: "bg-[#FBE9E7] text-[#9A2D20]",
};

export function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
