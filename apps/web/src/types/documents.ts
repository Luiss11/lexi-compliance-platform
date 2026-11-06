export type DocumentStatus = "UPLOADED" | "PROCESSING" | "INDEXED" | "NEEDS_REVIEW" | "ERROR";

export interface DocumentItem {
  id: string;
  title: string;
  category: string;
  status: DocumentStatus;
  pages: number | null;
  chunks: number | null;
  sha256: string;
  uploaded_by_name: string | null;
  created_at: string;
}

export const CATEGORIES = ["Ley", "Norma oficial", "Reglamento", "Contrato", "Política interna", "Otro"];

// El agente de vacíos solo analiza estos tipos: son obligaciones que vienen de fuera de la empresa
export const EXTERNAL_CATEGORIES = ["Ley", "Norma oficial", "Reglamento", "Contrato"];

export const STATUS_INFO: Record<DocumentStatus, { label: string; hint: string; style: string }> = {
  UPLOADED: {
    label: "Guardado",
    hint: "Sellado con SHA-256. Aún sin indexar para el asistente.",
    style: "bg-paper-deep text-ink",
  },
  PROCESSING: {
    label: "Indexando",
    hint: "Se está preparando para el asistente.",
    style: "bg-warn-soft text-warn",
  },
  INDEXED: {
    label: "Indexado",
    hint: "Listo para consultas del asistente.",
    style: "bg-lexi-soft text-lexi",
  },
  NEEDS_REVIEW: {
    label: "Requiere revisión",
    hint: "El PDF no tiene texto (parece escaneado). Sube una versión con texto.",
    style: "bg-warn-soft text-warn",
  },
  ERROR: {
    label: "Error al indexar",
    hint: "Falló la indexación. Puedes reintentarla.",
    style: "bg-danger-soft text-danger",
  },
};
