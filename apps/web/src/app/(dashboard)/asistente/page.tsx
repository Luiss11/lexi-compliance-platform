"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { CitationCard } from "@/components/ui/CitationCard";
import type { QueryResponse } from "@/types/rag";

export default function AsistentePage() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function ask() {
    if (question.trim().length < 3) return;
    setLoading(true);
    setError(null);
    try {
      // TODO: leer token de la cookie en un route handler para no exponerlo al cliente
      setResult(await api<QueryResponse>("/query", { method: "POST", body: JSON.stringify({ question }) }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo consultar");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-wrap gap-8">
      <section className="flex min-w-0 flex-[3_1_520px] flex-col gap-5">
        <h1 className="font-serif text-3xl font-semibold">Asistente legal</h1>
        <p className="text-sm text-muted">Responde solo con base en los documentos de tu organización.</p>

        {result && (
          <div className={`rounded-lg border p-5 leading-relaxed ${result.grounded ? "border-line bg-white" : "border-[#E6D3AE] bg-[#FBF7EE]"}`}>
            <div className={`mb-2 text-sm font-semibold ${result.grounded ? "text-lexi" : "text-warn"}`}>
              {result.grounded ? `Respuesta fundamentada · ${result.citations.length} citas` : `Sin fundamento suficiente · mejor similitud ${result.best_score.toFixed(2)}`}
            </div>
            <p className="whitespace-pre-line">{result.answer}</p>
          </div>
        )}
        {error && <p role="alert" className="text-sm text-danger">{error}</p>}

        <div className="flex items-end gap-2.5 rounded-lg border border-[#C9C5B9] bg-white p-2.5">
          <label htmlFor="q" className="sr-only">Pregunta</label>
          <textarea id="q" rows={2} value={question} onChange={(e) => setQuestion(e.target.value)}
            placeholder="Pregunta sobre tus obligaciones legales, permisos o contratos…"
            className="flex-1 resize-none bg-transparent px-2 py-1.5 outline-none" />
          <button onClick={ask} disabled={loading} className="h-11 rounded-md bg-lexi px-4 font-medium text-white disabled:opacity-60">
            {loading ? "Buscando…" : "Preguntar"}
          </button>
        </div>
      </section>

      <aside aria-label="Fuentes citadas" className="flex min-w-0 flex-[1_1_300px] flex-col gap-3">
        <h2 className="font-semibold">Fuentes citadas</h2>
        {result?.citations.map((c, i) => <CitationCard key={`${c.document_id}-${i}`} c={c} index={i + 1} />)}
      </aside>
    </div>
  );
}
