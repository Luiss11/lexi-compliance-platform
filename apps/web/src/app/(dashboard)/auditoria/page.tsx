import Link from "next/link";
import { redirect } from "next/navigation";
import { API_URL, getToken } from "@/lib/session";
import { ACTION_LABEL, describe, type AuditEntry } from "@/types/audit";

const PAGE_SIZE = 25;

async function load(action: string | undefined, page: number) {
  const token = getToken();
  if (!token) redirect("/logout");
  const q = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String((page - 1) * PAGE_SIZE) });
  if (action && ACTION_LABEL[action]) q.set("action", action);
  try {
    const res = await fetch(`${API_URL}/audit?${q}`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    if (res.status === 401) redirect("/logout");
    if (res.status === 503) return { notReady: true as const };
    if (!res.ok) return null;
    return (await res.json()) as { items: AuditEntry[]; total: number };
  } catch {
    return null;
  }
}

function when(iso: string) {
  const d = new Date(iso.endsWith("Z") ? iso : `${iso}Z`);
  return d.toLocaleString("es-MX", { dateStyle: "short", timeStyle: "medium", timeZone: "America/Mexico_City" });
}

const ALERT = new Set(["EVIDENCE_TAMPERED"]);

// Filtros rápidos: los eventos que más se consultan en una revisión
const FILTERS: { action?: string; label: string }[] = [
  { label: "Todo" },
  { action: "EVIDENCE_UPLOADED", label: "Evidencias subidas" },
  { action: "TASK_STATUS_CHANGED", label: "Cambios de estado" },
  { action: "EVIDENCE_REVIEWED", label: "Revisiones IA" },
  { action: "EVIDENCE_TAMPERED", label: "Alteraciones" },
  { action: "DOSSIER_GENERATED", label: "Expedientes" },
];

export default async function AuditoriaPage({
  searchParams,
}: {
  searchParams: { action?: string; page?: string };
}) {
  const page = Math.max(1, Number(searchParams.page) || 1);
  const action = searchParams.action && ACTION_LABEL[searchParams.action] ? searchParams.action : undefined;
  const data = await load(action, page);

  const href = (a: string | undefined, p: number) => {
    const q = new URLSearchParams();
    if (a) q.set("action", a);
    if (p > 1) q.set("page", String(p));
    const s = q.toString();
    return `/auditoria${s ? `?${s}` : ""}`;
  };

  return (
    <div className="flex max-w-5xl flex-col gap-6">
      <header>
        <h1 className="font-serif text-3xl font-semibold">Auditoría</h1>
        <p className="mt-2 text-sm text-muted">
          Registro de quién hizo qué y cuándo. Solo se agrega información: no se edita ni se borra.
        </p>
      </header>

      <nav aria-label="Filtros" className="flex flex-wrap gap-2">
        {FILTERS.map((f) => {
          const active = f.action === action;
          return (
            <Link
              key={f.label}
              href={href(f.action, 1)}
              aria-current={active ? "page" : undefined}
              className={`flex min-h-11 items-center rounded-md border px-3 text-sm ${
                active ? "border-lexi bg-lexi text-white" : "border-line bg-white hover:bg-[#F5F4EF]"
              }`}
            >
              {f.label}
            </Link>
          );
        })}
      </nav>

      {data === null ? (
        <div role="alert" className="rounded-md border border-line bg-white px-4 py-3 text-sm">
          No se pudo cargar la bitácora. Revisa que la API esté encendida.
        </div>
      ) : "notReady" in data ? (
        <div role="alert" className="rounded-md border border-[#E7B8B1] bg-[#FBE9E7] px-4 py-3 text-sm text-[#9A2D20]">
          La bitácora aún no está lista: falta crear la tabla <code>audit_logs</code> en la base de datos.
        </div>
      ) : data.items.length === 0 ? (
        <p className="rounded-lg border border-dashed border-line bg-white px-4 py-10 text-center text-sm text-muted">
          Aún no hay eventos {action ? "de este tipo" : "registrados"}.
        </p>
      ) : (
        <>
          <ul className="flex flex-col divide-y divide-line rounded-lg border border-line bg-white">
            {data.items.map((e) => (
              <li key={e.id} className="flex flex-wrap items-start justify-between gap-x-4 gap-y-1 px-4 py-3 text-sm">
                <div className="min-w-0 flex-1">
                  <p className={`font-medium ${ALERT.has(e.action) ? "text-[#9A2D20]" : ""}`}>
                    {ACTION_LABEL[e.action] ?? e.action}
                  </p>
                  <p className="break-words text-xs text-muted">{describe(e)}</p>
                </div>
                <div className="text-right text-xs text-muted">
                  <p>{e.actor_name ?? "Sistema"}</p>
                  <p>{when(e.created_at)}</p>
                </div>
              </li>
            ))}
          </ul>

          <div className="flex items-center justify-between text-sm">
            <span className="text-muted">
              {data.total} evento(s) · página {page} de {Math.max(1, Math.ceil(data.total / PAGE_SIZE))}
            </span>
            <div className="flex gap-2">
              {page > 1 && (
                <Link href={href(action, page - 1)} className="flex min-h-11 items-center rounded-md border border-line bg-white px-4">
                  ← Anterior
                </Link>
              )}
              {page * PAGE_SIZE < data.total && (
                <Link href={href(action, page + 1)} className="flex min-h-11 items-center rounded-md border border-line bg-white px-4">
                  Siguiente →
                </Link>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
