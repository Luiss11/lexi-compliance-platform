import Link from "next/link";
import { redirect } from "next/navigation";
import { API_URL, getSession, getToken } from "@/lib/session";
import type { Alert, Dashboard, Upcoming } from "@/types/report";

async function loadDashboard(): Promise<Dashboard | null> {
  const token = getToken();
  if (!token) redirect("/logout");
  try {
    const res = await fetch(`${API_URL}/dashboard`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    if (res.status === 401) redirect("/logout");
    return res.ok ? ((await res.json()) as Dashboard) : null;
  } catch {
    return null;
  }
}

const SEVERITY_STYLE: Record<Alert["severity"], { dot: string; label: string }> = {
  high: { dot: "bg-danger-bright", label: "Urgente" },
  medium: { dot: "bg-warn-bright", label: "Atención" },
  info: { dot: "bg-info-bright", label: "Pendiente" },
};

const PRIORITY_STYLE = {
  ALTA: "bg-danger-soft text-danger",
  MEDIA: "bg-warn-soft text-warn",
  BAJA: "bg-lexi-soft text-lexi",
} as const;

// Clases completas (no interpoladas) para que Tailwind las genere
const SCORE_TONE = {
  empty: { stroke: "stroke-ink-faint", text: "text-muted" },
  ok: { stroke: "stroke-lexi-bright", text: "text-lexi" },
  mid: { stroke: "stroke-warn-bright", text: "text-warn" },
  low: { stroke: "stroke-danger-bright", text: "text-danger" },
} as const;

function scoreTone(score: number, total: number) {
  if (total === 0) return SCORE_TONE.empty;
  if (score >= 80) return SCORE_TONE.ok;
  if (score >= 50) return SCORE_TONE.mid;
  return SCORE_TONE.low;
}

function ScoreRing({ score, total }: { score: number; total: number }) {
  const r = 52;
  const c = 2 * Math.PI * r;
  const tone = scoreTone(score, total);
  return (
    <svg viewBox="0 0 120 120" className="h-36 w-36 shrink-0" role="img" aria-label={`Índice de cumplimiento: ${score} de 100`}>
      <circle cx="60" cy="60" r={r} fill="none" strokeWidth="11" className="stroke-paper-deep" />
      <circle
        cx="60" cy="60" r={r} fill="none" strokeWidth="11" strokeLinecap="round" className={tone.stroke}
        strokeDasharray={`${(c * score) / 100} ${c}`} transform="rotate(-90 60 60)"
      />
      <text x="60" y="66" textAnchor="middle" className="fill-ink font-serif" fontSize="30" fontWeight="600">
        {total === 0 ? "—" : score}
      </text>
    </svg>
  );
}

function dueText(u: Upcoming) {
  if (u.days_left < 0) return `Venció hace ${-u.days_left} d`;
  if (u.days_left === 0) return "Vence hoy";
  if (u.days_left === 1) return "Vence mañana";
  return `En ${u.days_left} días`;
}

function Kpi({ label, value, hint, danger }: { label: string; value: string; hint?: string; danger?: boolean }) {
  return (
    <div className="rounded-lg border border-line bg-white p-5">
      <div className="text-sm text-muted">{label}</div>
      <div className={`mt-2 font-serif text-4xl font-semibold ${danger ? "text-danger-bright" : ""}`}>{value}</div>
      {hint && <div className="mt-1 text-xs text-muted">{hint}</div>}
    </div>
  );
}

export default async function PanelPage() {
  const me = await getSession();
  const firstName = me?.user.full_name.split(" ")[0] ?? "";
  const isManager = me?.user.role === "ADMIN" || me?.user.role === "COMPLIANCE";
  const d = await loadDashboard();

  const segments = d
    ? [
        { label: "Pendientes", n: d.counts.backlog, color: "bg-ink-dim" },
        { label: "En curso", n: d.counts.in_progress, color: "bg-warn-bright" },
        { label: "En revisión", n: d.counts.in_review, color: "bg-info-bright" },
        { label: "Cumplidas", n: d.counts.done, color: "bg-lexi-bright" },
      ]
    : [];

  return (
    <div className="flex flex-col gap-7">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-serif text-3xl font-semibold">Hola, {firstName}</h1>
          <p className="mt-1 text-sm text-muted">
            {d?.scope === "mine"
              ? `Tus obligaciones asignadas en ${me?.tenant.name}.`
              : `Estado de cumplimiento de ${me?.tenant.name}.`}
          </p>
        </div>
        {isManager && (
          <div className="flex flex-wrap gap-2">
            <Link href="/vacios" className="flex min-h-11 items-center rounded-md border border-line bg-white px-4 text-sm hover:bg-paper">
              Buscar vacíos normativos
            </Link>
            <Link href="/expediente" className="flex min-h-11 items-center rounded-md bg-lexi px-4 text-sm font-medium text-white">
              Generar expediente de auditoría
            </Link>
          </div>
        )}
      </header>

      {!d ? (
        <div role="alert" className="rounded-md border border-line bg-white px-4 py-3 text-sm">
          No se pudo cargar el panel. Revisa que la API esté encendida.
        </div>
      ) : d.total_tasks === 0 ? (
        <p className="rounded-lg border border-dashed border-line bg-white px-4 py-10 text-center text-sm text-muted">
          Aún no hay obligaciones registradas. Crea la primera en <Link href="/tareas" className="underline">Tareas</Link>.
        </p>
      ) : (
        <>
          <section className="grid gap-4 lg:grid-cols-[minmax(320px,1.2fr)_2fr]">
            <div className="flex items-center gap-5 rounded-lg border border-line bg-white p-5">
              <ScoreRing score={d.score} total={d.total_tasks} />
              <div>
                <div className="text-sm text-muted">Índice de cumplimiento</div>
                <div className={`font-serif text-2xl font-semibold ${scoreTone(d.score, d.total_tasks).text}`}>
                  {d.score_label}
                </div>
                <p className="mt-2 text-xs leading-relaxed text-muted">
                  Ponderado por prioridad. Una tarea cumplida sin evidencia sellada cuenta solo la mitad.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-[repeat(auto-fit,minmax(170px,1fr))] gap-4">
              <Kpi
                label="Tareas vencidas"
                value={String(d.overdue)}
                hint={d.due_soon ? `${d.due_soon} vencen en 14 días o menos` : "Nada por vencer pronto"}
                danger={d.overdue > 0}
              />
              <Kpi
                label="Cobertura de evidencia"
                value={d.evidence_coverage === null ? "—" : `${d.evidence_coverage}%`}
                hint={`${d.evidence_files} archivo(s) sellados con SHA-256`}
              />
              {d.documents_total !== null ? (
                <Kpi
                  label="Normativa indexada"
                  value={`${d.documents_indexed}/${d.documents_total}`}
                  hint="Documentos disponibles para el asistente"
                />
              ) : (
                <Kpi label="Mis tareas" value={String(d.total_tasks)} hint={`${d.counts.done} cumplidas`} />
              )}
            </div>
          </section>

          <section className="rounded-lg border border-line bg-white p-5">
            <h2 className="text-sm font-semibold">Avance de las obligaciones</h2>
            <div className="mt-3 flex h-3 overflow-hidden rounded-full bg-paper-deep" role="img"
              aria-label={segments.map((s) => `${s.label}: ${s.n}`).join(", ")}>
              {segments.map((s) =>
                s.n > 0 ? <div key={s.label} className={s.color} style={{ width: `${(s.n / d.total_tasks) * 100}%` }} /> : null,
              )}
            </div>
            <ul className="mt-3 flex flex-wrap gap-x-6 gap-y-1 text-sm">
              {segments.map((s) => (
                <li key={s.label} className="flex items-center gap-2">
                  <span className={`h-2.5 w-2.5 rounded-sm ${s.color}`} />
                  {s.label} <span className="font-semibold">{s.n}</span>
                </li>
              ))}
            </ul>
          </section>

          <section className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-lg border border-line bg-white p-5">
              <h2 className="text-sm font-semibold">Requiere atención</h2>
              {d.alerts.length === 0 ? (
                <p className="mt-3 text-sm text-muted">Todo en orden. No hay alertas abiertas.</p>
              ) : (
                <ul className="mt-3 flex flex-col divide-y divide-line">
                  {d.alerts.map((a, i) => (
                    <li key={`${a.kind}-${a.task_id ?? i}`} className="flex items-start gap-3 py-2.5 text-sm">
                      <span className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${SEVERITY_STYLE[a.severity].dot}`} aria-hidden />
                      <span className="sr-only">{SEVERITY_STYLE[a.severity].label}: </span>
                      <span className="flex-1">{a.message}</span>
                      {a.task_id && (
                        <Link href={`/tareas/${a.task_id}/evidencia`} className="shrink-0 text-xs text-lexi underline">
                          Abrir
                        </Link>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="rounded-lg border border-line bg-white p-5">
              <h2 className="text-sm font-semibold">Próximos vencimientos</h2>
              {d.upcoming.length === 0 ? (
                <p className="mt-3 text-sm text-muted">Sin vencimientos en los próximos 14 días.</p>
              ) : (
                <ul className="mt-3 flex flex-col divide-y divide-line">
                  {d.upcoming.map((u) => (
                    <li key={u.task_id} className="flex items-center justify-between gap-3 py-2.5 text-sm">
                      <div className="min-w-0">
                        <div className="truncate">
                          <span className="font-mono text-xs text-muted">{u.code}</span> {u.title}
                        </div>
                        <div className={`text-xs ${u.days_left < 0 ? "font-medium text-danger-bright" : "text-muted"}`}>
                          {dueText(u)}
                          {u.assignee_name ? ` · ${u.assignee_name}` : ""}
                        </div>
                      </div>
                      <span className={`shrink-0 rounded px-2 py-0.5 text-xs ${PRIORITY_STYLE[u.priority]}`}>{u.priority}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
