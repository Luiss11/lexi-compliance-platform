"use client";

import { useFormState, useFormStatus } from "react-dom";
import { askAction, type AskState } from "./actions";

const INITIAL: AskState = { question: "", result: null, error: null };

function SubmitButton() {
  const { pending } = useFormStatus();
  return (
    <button
      type="submit"
      disabled={pending}
      className="min-h-11 rounded-md bg-lexi px-5 text-sm font-medium text-white disabled:opacity-60"
    >
      {pending ? "Consultando…" : "Preguntar"}
    </button>
  );
}

export function AskForm({ showScore }: { showScore: boolean }) {
  const [state, formAction] = useFormState(askAction, INITIAL);
  const { result } = state;

  return (
    <div className="flex flex-col gap-5">
      <form action={formAction} className="flex flex-col gap-3 rounded-lg border border-line bg-white p-4">
        <label htmlFor="question" className="text-sm font-medium">
          Tu pregunta
        </label>
        <textarea
          id="question"
          name="question"
          rows={3}
          required
          minLength={3}
          maxLength={2000}
          defaultValue={state.question}
          placeholder="Ej.: ¿Qué debe contener el aviso de privacidad?"
          className="rounded-md border border-line px-3 py-2 text-sm"
        />
        <div>
          <SubmitButton />
        </div>
      </form>

      {state.error && (
        <div role="alert" className="rounded-md border border-[#E7B8B1] bg-[#FBE9E7] px-4 py-3 text-sm text-[#9A2D20]">
          {state.error}
        </div>
      )}

      {result && (
        <section aria-live="polite" className="flex flex-col gap-4 rounded-lg border border-line bg-white p-5">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-sm font-semibold">Respuesta</h2>
            <span
              className={`rounded px-2 py-0.5 text-xs font-medium ${
                result.grounded ? "bg-[#E6F1EF] text-lexi" : "bg-[#FFF3D6] text-[#7A5600]"
              }`}
            >
              {result.grounded ? "Con soporte documental" : "Sin soporte documental"}
            </span>
            {showScore && (
              <span className="text-xs text-muted" title="Similitud coseno máxima encontrada (el corte es 0.75)">
                similitud máx. {result.best_score.toFixed(2)}
              </span>
            )}
          </div>

          <p className="whitespace-pre-wrap text-[15px] leading-relaxed">{result.answer}</p>

          {result.citations.length > 0 && (
            <div className="flex flex-col gap-2 border-t border-line pt-4">
              <h3 className="text-sm font-semibold">Fuentes</h3>
              <ol className="flex flex-col gap-2">
                {result.citations.map((c, i) => (
                  <li key={`${c.document_id}-${i}`} className="rounded-md bg-[#F5F4EF] p-3 text-sm">
                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                      <span className="font-medium">
                        [{i + 1}] {c.document_title}
                      </span>
                      <span className="text-xs text-muted">
                        p. {c.page}
                        {c.clause ? ` · ${c.clause}` : ""}
                        {showScore ? ` · ${c.score.toFixed(2)}` : ""}
                      </span>
                    </div>
                    <details className="mt-1">
                      <summary className="cursor-pointer text-xs text-muted">Ver fragmento</summary>
                      <p className="mt-1 whitespace-pre-wrap text-xs text-muted">{c.excerpt}</p>
                    </details>
                  </li>
                ))}
              </ol>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
