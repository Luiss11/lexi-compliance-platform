export interface Citation {
  document_id: string;
  document_title: string;
  page: number;
  clause: string | null;
  score: number;
  excerpt: string;
}

export interface QueryResponse {
  answer: string;
  grounded: boolean;
  best_score: number;
  citations: Citation[];
}

export const FALLBACK_MESSAGE =
  "No se encontró documento de soporte autorizado en la base de conocimiento.";
