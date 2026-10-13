import { redirect } from "next/navigation";
import { API_URL, getSession, getToken } from "@/lib/session";
import { CATEGORIES, STATUS_INFO, type DocumentItem } from "@/types/documents";
import { reindexDocumentAction, uploadDocumentAction } from "./actions";

async function loadDocuments(): Promise<DocumentItem[] | null> {
  const token = getToken();
  if (!token) redirect("/logout");
  try {
    const res = await fetch(`${API_URL}/documents`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    if (res.status === 401) redirect("/logout");
    if (!res.ok) return null;
    return ((await res.json()) as { items: DocumentItem[] }).items;
  } catch {
    return null;
  }
}

function formatDate(iso: string) {
  const [y, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}/${y}`;
}

export default async function DocumentosPage({
  searchParams,
}: {
  searchParams: { error?: string; ok?: string };
}) {
  const me = await getSession();
  if (!me) redirect("/logout");
  const docs = await loadDocuments();

  return (
    <div className="flex flex-col gap-6">
      <header>
        <h1 className="font-serif text-3xl font-semibold">Documentos</h1>
        <p className="mt-1 text-sm text-muted">
          Leyes, normas y políticas de tu organización. Cada PDF se sella con SHA-256 al subirlo.
        </p>
      </header>

      {searchParams.error && (
        <div role="alert" className="rounded-md border border-[#E7B8B1] bg-[#FBE9E7] px-4 py-3 text-sm text-[#9A2D20]">
          {searchParams.error}
        </div>
      )}
      {searchParams.ok && (
        <div role="status" className="rounded-md border border-[#B7D6D2] bg-[#E6F1EF] px-4 py-3 text-sm text-lexi">
          {searchParams.ok}
        </div>
      )}
      {docs === null && (
        <div role="alert" className="rounded-md border border-line bg-white px-4 py-3 text-sm">
          No se pudieron cargar los documentos. Revisa que la API esté encendida.
        </div>
      )}

      <form
        action={uploadDocumentAction}
        encType="multipart/form-data"
        className="grid gap-3 rounded-lg border border-line bg-white p-4 sm:grid-cols-2"
      >
        <h2 className="text-sm font-semibold sm:col-span-2">Subir documento</h2>
        <label className="flex flex-col gap-1 text-sm sm:col-span-2">
          Archivo PDF (máximo 20 MB)
          <input
            type="file"
            name="file"
            accept="application/pdf,.pdf"
            required
            className="min-h-11 rounded-md border border-line px-3 py-2 text-sm"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Categoría
          <select name="category" defaultValue="Ley" className="min-h-11 rounded-md border border-line px-3">
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Título (opcional)
          <input
            name="title"
            maxLength={200}
            placeholder="Si lo dejas vacío usa el nombre del archivo"
            className="min-h-11 rounded-md border border-line px-3"
          />
        </label>
        <div className="sm:col-span-2">
          <button type="submit" className="min-h-11 rounded-md bg-lexi px-5 text-sm font-medium text-white">
            Subir y sellar
          </button>
        </div>
      </form>

      <section className="flex flex-col gap-3">
        <h2 className="text-sm font-semibold">
          Biblioteca {docs ? <span className="font-normal text-muted">({docs.length})</span> : null}
        </h2>
        {docs && docs.length === 0 && (
          <p className="rounded-lg border border-dashed border-line bg-white px-4 py-8 text-center text-sm text-muted">
            Aún no hay documentos. Sube el primer PDF para empezar.
          </p>
        )}
        {docs?.map((d) => {
          const info = STATUS_INFO[d.status];
          const canRetry = d.status === "ERROR" || d.status === "UPLOADED";
          return (
            <article key={d.id} className="flex flex-col gap-2 rounded-lg border border-line bg-white p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="font-medium">{d.title}</h3>
                <span title={info.hint} className={`rounded px-2 py-0.5 text-xs font-medium ${info.style}`}>
                  {info.label}
                </span>
              </div>
              <p className="text-xs text-muted">
                {d.category} · {d.pages ?? "?"} pág. · {formatDate(d.created_at)}
                {d.uploaded_by_name ? ` · ${d.uploaded_by_name}` : ""}
                {d.chunks ? ` · ${d.chunks} fragmentos` : ""}
              </p>
              <p className="break-all font-mono text-[11px] text-muted" title="Huella SHA-256 del archivo">
                SHA-256: {d.sha256}
              </p>
              <p className="text-xs text-muted">{info.hint}</p>
              {canRetry && (
                <form action={reindexDocumentAction}>
                  <input type="hidden" name="id" value={d.id} />
                  <button type="submit" className="min-h-11 rounded-md border border-line px-3 text-xs hover:bg-[#F5F4EF]">
                    Indexar para el asistente
                  </button>
                </form>
              )}
            </article>
          );
        })}
      </section>
    </div>
  );
}
