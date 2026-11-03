import { redirect } from "next/navigation";
import { API_URL, getToken } from "@/lib/session";
import { SECTOR_LABEL, type ObligationList } from "@/types/obligations";
import { ObligationsPanel } from "./ObligationsPanel";

async function fetchCatalog(): Promise<ObligationList | null> {
  const token = getToken();
  if (!token) redirect("/logout");
  try {
    const res = await fetch(`${API_URL}/compliance/obligations`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    if (res.status === 401) redirect("/logout");
    if (!res.ok) return null;
    return (await res.json()) as ObligationList;
  } catch {
    return null;
  }
}

export default async function ObligacionesPage() {
  const catalog = await fetchCatalog();

  return (
    <div className="flex max-w-4xl flex-col gap-6">
      <header>
        <h1 className="font-serif text-3xl font-semibold">Obligaciones de tu sector</h1>
        <p className="mt-2 text-sm text-muted">
          Catálogo de obligaciones que suelen aplicar a tu giro
          {catalog?.sector ? ` (${SECTOR_LABEL[catalog.sector]})` : ""}, cada una con su norma y su artículo o numeral.
          Elige cuáles quieres convertir en tareas de cumplimiento.
        </p>
      </header>

      {catalog === null ? (
        <div role="alert" className="rounded-md border border-[#E7B8B1] bg-[#FBE9E7] px-4 py-3 text-sm text-[#9A2D20]">
          No se pudo cargar el catálogo. Intenta de nuevo en un momento.
        </div>
      ) : (
        <ObligationsPanel catalog={catalog} />
      )}
    </div>
  );
}
