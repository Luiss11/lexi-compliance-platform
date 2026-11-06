"use client";

import Link from "next/link";
import { useState } from "react";
import { useFormState, useFormStatus } from "react-dom";
import { FRECUENCIA_LABEL, type ObligationItem, type ObligationList } from "@/types/obligations";
import { loadObligationsAction, type LoadState } from "./actions";

const S0: LoadState = { created: null, skipped: 0, error: null };

function Submit({ count }: { count: number }) {
  const { pending } = useFormStatus();
  return (
    <button
      type="submit"
      disabled={pending || count === 0}
      className="min-h-11 rounded-md bg-lexi px-5 text-sm font-medium text-white disabled:opacity-60"
    >
      {pending ? "Creando…" : `Crear ${count} tarea(s)`}
    </button>
  );
}

function Banner({ tone, children }: { tone: "error" | "ok"; children: React.ReactNode }) {
  const style =
    tone === "error" ? "border-danger-line bg-danger-soft text-danger" : "border-lexi-line bg-lexi-soft text-lexi";
  return (
    <div role={tone === "error" ? "alert" : "status"} className={`rounded-md border px-4 py-3 text-sm ${style}`}>
      {children}
    </div>
  );
}

function Badge({ item }: { item: ObligationItem }) {
  if (item.estado_verificacion === "verificado") return null;
  return (
    <span className="rounded bg-warn-soft px-2 py-0.5 text-xs font-medium text-warn">
      {item.estado_verificacion === "parcial" ? "Por confirmar en fuente oficial" : "Pendiente de verificar"}
    </span>
  );
}

export function ObligationsPanel({ catalog }: { catalog: ObligationList }) {
  const [state, action] = useFormState(loadObligationsAction, S0);
  // Por omisión no se marca nada: la persona decide qué asumir
  const [picked, setPicked] = useState<Record<string, boolean>>({});

  const pending = catalog.items.filter((i) => !i.loaded);
  const count = pending.filter((i) => picked[i.id]).length;
  const groups = [...new Set(catalog.items.map((i) => i.norma))];

  function toggleAll(on: boolean) {
    setPicked(Object.fromEntries(pending.map((i) => [i.id, on])));
  }

  return (
    <form action={action} className="flex flex-col gap-4">
      {state.created !== null && (
        <Banner tone="ok">
          Se crearon {state.created.length} tarea(s){state.created.length > 0 ? `: ${state.created.join(", ")}` : ""}.
          {state.skipped > 0 && ` ${state.skipped} ya estaban cargadas y no se repitieron.`} Quedaron en «Pendientes»; ajusta
          responsables y fechas en el tablero.{" "}
          <Link href="/tareas" className="underline">
            Ir al tablero
          </Link>
        </Banner>
      )}
      {state.error && <Banner tone="error">{state.error}</Banner>}

      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-line bg-white p-4">
        <p className="min-w-0 flex-1 text-sm text-muted">
          {catalog.items.length} obligaciones · {catalog.items.filter((i) => i.loaded).length} ya cargadas como tarea.
        </p>
        <button type="button" onClick={() => toggleAll(true)} className="min-h-11 rounded-md border border-line px-4 text-sm hover:bg-paper">
          Marcar las pendientes
        </button>
        <button type="button" onClick={() => toggleAll(false)} className="min-h-11 rounded-md border border-line px-4 text-sm hover:bg-paper">
          Quitar marcas
        </button>
      </div>

      {groups.map((norma) => {
        const items = catalog.items.filter((i) => i.norma === norma);
        return (
          <section key={norma} className="flex flex-col gap-2">
            <h2 className="text-sm font-semibold">
              {norma}
              <span className="ml-2 font-normal text-muted">{items[0].publicacion}</span>
            </h2>
            {items.map((i) => {
              const checked = !i.loaded && (picked[i.id] ?? false);
              return (
                <label
                  key={i.id}
                  className={`flex gap-3 rounded-lg border bg-white p-4 ${i.loaded ? "opacity-60" : "cursor-pointer"} ${checked ? "border-lexi" : "border-line"}`}
                >
                  <input
                    type="checkbox"
                    name="pick"
                    value={i.id}
                    disabled={i.loaded}
                    checked={checked}
                    onChange={(e) => setPicked((p) => ({ ...p, [i.id]: e.target.checked }))}
                    className="mt-1 h-5 w-5 shrink-0 accent-lexi-bright"
                  />
                  <div className="flex min-w-0 flex-1 flex-col gap-2">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <h3 className="font-medium">{i.titulo}</h3>
                      <div className="flex flex-wrap gap-2">
                        {i.loaded && <span className="rounded bg-lexi-soft px-2 py-0.5 text-xs font-medium text-lexi">Ya es tarea</span>}
                        <Badge item={i} />
                        <span className="rounded bg-paper px-2 py-0.5 text-xs">{FRECUENCIA_LABEL[i.frecuencia]}</span>
                      </div>
                    </div>
                    <p className="text-sm">{i.obligacion}</p>
                    <p className="text-xs text-muted">Evidencia sugerida: {i.evidencia_sugerida}</p>
                    {i.cita_textual && (
                      <blockquote className="border-l-2 border-line pl-3 text-xs italic text-muted">
                        «{i.cita_textual}»
                        <span className="mt-0.5 block not-italic">— {i.norma}, {i.cita}</span>
                      </blockquote>
                    )}
                    {!i.cita_textual && <p className="text-xs text-muted">Fundamento: {i.norma}, {i.cita}</p>}
                    {i.nota && <p className="text-xs text-muted">Nota: {i.nota}</p>}
                  </div>
                </label>
              );
            })}
          </section>
        );
      })}

      <div className="sticky bottom-0 flex flex-wrap items-center gap-3 border-t border-line bg-paper-soft py-3">
        <Submit count={count} />
        <p className="text-xs text-muted">Las fechas son una propuesta inicial; ajústalas según tu caso.</p>
      </div>
      <p className="text-xs text-muted">{catalog.aviso}</p>
    </form>
  );
}
