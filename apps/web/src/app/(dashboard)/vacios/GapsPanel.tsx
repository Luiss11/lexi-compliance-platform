"use client";

import Link from "next/link";
import { useState } from "react";
import { useFormState, useFormStatus } from "react-dom";
import { PRIORITY_LABEL } from "@/types/tasks";
import { citationOf, type GapAnalysis } from "@/types/gaps";
import {
  acceptGapsAction,
  analyzeGapsAction,
  dismissGapsAction,
  type AcceptState,
  type AnalyzeState,
  type DismissState,
} from "./actions";

const PRIORITY_STYLE = {
  ALTA: "bg-[#FBE9E7] text-[#9A2D20]",
  MEDIA: "bg-[#FFF3D6] text-[#7A5600]",
  BAJA: "bg-[#E6F1EF] text-lexi",
} as const;

function Submit({ label, pendingLabel }: { label: string; pendingLabel: string }) {
  const { pending } = useFormStatus();
  return (
    <button type="submit" disabled={pending} className="min-h-11 rounded-md bg-lexi px-5 text-sm font-medium text-white disabled:opacity-60">
      {pending ? pendingLabel : label}
    </button>
  );
}

function dueText(iso: string) {
  const [y, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}/${y}`;
}

const A0: AnalyzeState = { result: null, error: null };
const B0: AcceptState = { created: null, error: null };
const C0: DismissState = { dismissed: null, error: null };

function Banner({ tone, children }: { tone: "error" | "ok" | "plain"; children: React.ReactNode }) {
  const style =
    tone === "error"
      ? "border-[#E7B8B1] bg-[#FBE9E7] text-[#9A2D20]"
      : tone === "ok"
        ? "border-[#B7D6D2] bg-[#E6F1EF] text-lexi"
        : "border-line bg-white";
  return (
    <div role={tone === "error" ? "alert" : "status"} className={`rounded-md border px-4 py-3 text-sm ${style}`}>
      {children}
    </div>
  );
}

// Un componente por análisis (key): al analizar de nuevo, la selección y los avisos empiezan limpios
function Results({ result }: { result: GapAnalysis }) {
  const [accepted, accept] = useFormState(acceptGapsAction, B0);
  const [dismissed, dismiss] = useFormState(dismissGapsAction, C0);
  const [picked, setPicked] = useState<Record<string, boolean>>({});

  const { suggestions, stats } = result;
  const finished = accepted.created !== null || dismissed.dismissed !== null;
  const count = suggestions.filter((s) => picked[s.key] ?? true).length;
  const unchecked = suggestions.length - count;
  const error = accepted.error ?? dismissed.error;

  if (suggestions.length === 0) {
    return (
      <Banner tone="ok">
        <strong>No encontré vacíos nuevos.</strong> Revisé {stats.passages} fragmentos de {stats.documents} documento(s)
        contra tus {stats.existing_tasks} tarea(s).
        {stats.already_covered > 0 && ` ${stats.already_covered} propuesta(s) ya estaban cubiertas.`}
        {stats.dismissed_before > 0 && ` ${stats.dismissed_before} ya las habías descartado.`}
        {stats.not_obligation > 0 && ` ${stats.not_obligation} no eran obligaciones (solo descripciones).`}
        {stats.excluded_internal > 0 && ` ${stats.excluded_internal} fragmento(s) de políticas internas se omitieron.`}
      </Banner>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {accepted.created !== null && (
        <Banner tone="ok">
          Se crearon {accepted.created.length} tarea(s): {accepted.created.join(", ")}. Quedaron en «Pendientes», marcadas
          como sugeridas por IA y sin responsable.{" "}
          <Link href="/tareas" className="underline">
            Ir al tablero
          </Link>
        </Banner>
      )}
      {dismissed.dismissed !== null && (
        <Banner tone="plain">
          Descartaste {dismissed.dismissed} propuesta(s): no volverán a salir. Puedes analizar de nuevo cuando quieras.
        </Banner>
      )}
      {error && <Banner tone="error">{error}</Banner>}

      {!finished && (
        <form action={accept} className="flex flex-col gap-3">
          <input type="hidden" name="payload" value={JSON.stringify(suggestions)} />
          <p className="text-sm text-muted">
            {suggestions.length} vacío(s) detectado(s) · {stats.passages} fragmentos revisados
            {stats.discarded_unverified > 0 && ` · ${stats.discarded_unverified} descartado(s) por no poder verificar su cita`}
            {stats.already_covered > 0 && ` · ${stats.already_covered} ya cubierto(s)`}
            {stats.dismissed_before > 0 && ` · ${stats.dismissed_before} ya descartado(s)`}
            {stats.not_obligation > 0 && ` · ${stats.not_obligation} sin verbo de obligación`}
            {stats.excluded_internal > 0 && ` · ${stats.excluded_internal} fragmento(s) de políticas internas omitidos`}
          </p>

          {suggestions.map((s) => {
            const checked = picked[s.key] ?? true;
            return (
              <label
                key={s.key}
                className={`flex cursor-pointer gap-3 rounded-lg border bg-white p-4 ${checked ? "border-lexi" : "border-line"}`}
              >
                <input
                  type="checkbox"
                  name="pick"
                  value={s.key}
                  checked={checked}
                  onChange={(e) => setPicked((p) => ({ ...p, [s.key]: e.target.checked }))}
                  className="mt-1 h-5 w-5 shrink-0 accent-[#1F7A68]"
                />
                <div className="flex min-w-0 flex-1 flex-col gap-2">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h3 className="font-medium">{s.title}</h3>
                    <span className={`rounded px-2 py-0.5 text-xs font-medium ${PRIORITY_STYLE[s.priority]}`}>
                      {PRIORITY_LABEL[s.priority]} · vence {dueText(s.due_date)}
                    </span>
                  </div>
                  <p className="text-sm">{s.description}</p>
                  <p className="text-xs text-muted">Por qué: {s.reason}</p>
                  <blockquote className="border-l-2 border-line pl-3 text-xs italic text-muted">
                    «{s.quote}»
                    <span className="mt-0.5 block not-italic">— {citationOf(s)}</span>
                  </blockquote>
                </div>
              </label>
            );
          })}

          <div className="flex flex-wrap items-center gap-3">
            <Submit label={`Crear ${count} tarea(s) seleccionada(s)`} pendingLabel="Creando…" />
            {unchecked > 0 && (
              <button
                type="submit"
                formAction={dismiss}
                className="min-h-11 rounded-md border border-line bg-white px-4 text-sm hover:bg-[#F5F4EF]"
                title="Las sugerencias sin marcar se guardan como no aplicables y no vuelven a proponerse"
              >
                Descartar {unchecked} sin marcar
              </button>
            )}
          </div>
          <p className="text-xs text-muted">
            Las fechas son una propuesta: ajústalas en el tablero según el plazo legal que te aplique. Si no marcas una
            sugerencia y no la descartas, puede volver a salir en el próximo análisis.
          </p>
        </form>
      )}
    </div>
  );
}

export function GapsPanel() {
  const [analysis, analyze] = useFormState(analyzeGapsAction, A0);
  const [round, setRound] = useState(0);

  return (
    <div className="flex flex-col gap-5">
      <form
        action={(fd) => {
          setRound((r) => r + 1);
          analyze(fd);
        }}
        className="flex flex-col gap-3 rounded-lg border border-line bg-white p-4 sm:flex-row sm:items-center sm:justify-between"
      >
        <p className="text-sm text-muted">
          Lexi lee la normativa que cargaste y propone tareas para las obligaciones que todavía no tienen una. Cada
          propuesta trae la cita textual del documento; tú decides cuáles crear.
        </p>
        <Submit
          label={analysis.result ? "Analizar de nuevo" : "Analizar mi normativa"}
          pendingLabel="Analizando… (puede tardar unos segundos)"
        />
      </form>

      {analysis.error && <Banner tone="error">{analysis.error}</Banner>}
      {analysis.result && <Results key={round} result={analysis.result} />}
    </div>
  );
}
