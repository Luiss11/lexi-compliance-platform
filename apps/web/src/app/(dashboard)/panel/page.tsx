import { getSession } from "@/lib/session";

export default async function PanelPage() {
  const me = await getSession();
  const firstName = me?.user.full_name.split(" ")[0] ?? "";

  // TODO(Yosvanni): KPIs desde Prisma; vacíos desde POST /agent/audit-gaps
  return (
    <div className="flex flex-col gap-7">
      <header>
        <h1 className="font-serif text-3xl font-semibold">Hola, {firstName}</h1>
        <p className="mt-1 text-sm text-muted">
          Panel de cumplimiento de {me?.tenant.name}: índice, vacíos normativos y próximos
          vencimientos.
        </p>
      </header>
      <section className="grid grid-cols-[repeat(auto-fit,minmax(200px,1fr))] gap-4">
        {["Índice de cumplimiento", "Obligaciones mapeadas", "Tareas vencidas", "Evidencias validadas"].map(
          (k) => (
            <div key={k} className="rounded-lg border border-line bg-white p-5">
              <div className="text-sm text-muted">{k}</div>
              <div className="mt-2 font-serif text-4xl font-semibold">—</div>
            </div>
          ),
        )}
      </section>
    </div>
  );
}
