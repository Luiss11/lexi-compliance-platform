export type VerificationState = "verificado" | "parcial" | "pendiente";

export interface ObligationItem {
  id: string;
  sector: "todos" | "clinica" | "comercio";
  norma: string;
  norma_titulo: string;
  publicacion: string;
  cita: string;
  titulo: string;
  obligacion: string;
  frecuencia: "una_vez" | "anual" | "mensual" | "cada_2_meses" | "continua" | "por_evento";
  evidencia_sugerida: string;
  cita_textual: string | null;
  estado_verificacion: VerificationState;
  nota: string | null;
  loaded: boolean;
}

export interface ObligationList {
  sector: "clinica" | "comercio" | null;
  aviso: string;
  items: ObligationItem[];
}

export const FRECUENCIA_LABEL: Record<ObligationItem["frecuencia"], string> = {
  una_vez: "Una sola vez",
  anual: "Cada año",
  mensual: "Cada mes",
  cada_2_meses: "Cada 2 meses",
  continua: "Permanente",
  por_evento: "Cada vez que ocurra",
};

export const SECTOR_LABEL: Record<string, string> = {
  clinica: "Clínicas y consultorios",
  comercio: "Comercio y servicios",
};
