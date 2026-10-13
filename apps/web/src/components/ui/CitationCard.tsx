import type { Citation } from "@/types/rag";

export function CitationCard({ c, index }: { c: Citation; index: number }) {
  return (
    <article id={`cita${index}`} className="rounded-lg border border-line bg-white p-3.5">
      <div className="flex justify-between font-mono text-xs">
        <span className="font-medium text-lexi">[{index}] {c.document_title}</span>
        <span className="text-muted">{c.score.toFixed(2)}</span>
      </div>
      <div className="mt-1 text-xs text-muted">Página {c.page}{c.clause ? ` · ${c.clause}` : ""}</div>
      <p className="mt-2.5 text-sm leading-relaxed">{c.excerpt}</p>
    </article>
  );
}
