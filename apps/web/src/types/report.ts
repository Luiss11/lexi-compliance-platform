export interface Alert {
  kind: string;
  severity: "high" | "medium" | "info";
  message: string;
  task_id: string | null;
  task_code: string | null;
}

export interface Upcoming {
  task_id: string;
  code: string;
  title: string;
  due_date: string;
  days_left: number;
  priority: "ALTA" | "MEDIA" | "BAJA";
  status: string;
  assignee_name: string | null;
}

export interface Dashboard {
  scope: "tenant" | "mine";
  score: number;
  score_label: string;
  total_tasks: number;
  counts: { backlog: number; in_progress: number; in_review: number; done: number };
  overdue: number;
  due_soon: number;
  evidence_files: number;
  evidence_coverage: number | null;
  documents_total: number | null;
  documents_indexed: number | null;
  alerts: Alert[];
  upcoming: Upcoming[];
}

export type Integrity = "OK" | "TAMPERED" | "MISSING";

export interface DossierEvidence {
  id: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
  sha256: string;
  uploaded_by_name: string | null;
  uploaded_at: string;
  integrity: Integrity;
  ai_verdict: string | null;
  ai_summary: string | null;
}

export interface DossierTask {
  code: string;
  title: string;
  description: string | null;
  status: string;
  priority: "ALTA" | "MEDIA" | "BAJA";
  due_date: string | null;
  overdue: boolean;
  assignee_name: string | null;
  citation: string | null;
  document_title: string | null;
  evidence: DossierEvidence[];
}

export interface DossierDocument {
  title: string;
  category: string;
  status: string;
  pages: number | null;
  sha256: string;
  uploaded_at: string;
}

export interface DossierAudit {
  at: string;
  actor_name: string | null;
  action: string;
  entity_type: string;
  details: Record<string, unknown> | null;
}

export interface Dossier {
  tenant_name: string;
  generated_at: string;
  generated_by: string | null;
  summary: {
    score: number;
    score_label: string;
    total_tasks: number;
    done: number;
    overdue: number;
    evidence_files: number;
    integrity_failures: number;
    ai_flagged: number;
  };
  documents: DossierDocument[];
  tasks: DossierTask[];
  audit_trail: DossierAudit[];
  seal: string;
}
