import type { Priority } from "@/types/tasks";

export interface GapSuggestion {
  key: string;
  title: string;
  description: string;
  priority: Priority;
  due_date: string;
  reason: string;
  document_id: string;
  document_title: string;
  page: number;
  clause: string | null;
  quote: string;
}

export interface GapAnalysis {
  suggestions: GapSuggestion[];
  stats: {
    documents: number;
    passages: number;
    existing_tasks: number;
    excluded_internal: number;
    already_covered: number;
    dismissed_before: number;
    not_obligation: number;
    discarded_unverified: number;
  };
}

export function citationOf(s: Pick<GapSuggestion, "document_title" | "page" | "clause">): string {
  return `${s.document_title}, p. ${s.page}${s.clause ? `, ${s.clause}` : ""}`;
}
