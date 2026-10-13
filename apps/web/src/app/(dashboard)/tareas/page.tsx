const COLUMNS = [
  { key: "BACKLOG", title: "Por hacer" },
  { key: "IN_PROGRESS", title: "En progreso" },
  { key: "IN_REVIEW", title: "En revisión" },
  { key: "DONE", title: "Completada" },
] as const;

export default function TareasPage() {
  // TODO(Yosvanni): cargar tareas por status con prisma.task.findMany({ where: { tenantId } })
  return (
    <div className="flex flex-col gap-6">
      <h1 className="font-serif text-3xl font-semibold">Tareas de cumplimiento</h1>
      <div className="overflow-x-auto">
        <div className="grid min-w-[1040px] grid-cols-4 gap-4">
          {COLUMNS.map((col) => (
            <section key={col.key} className="min-h-64 rounded-xl bg-[#ECEAE3] p-3.5">
              <h2 className="text-sm font-semibold">{col.title}</h2>
            </section>
          ))}
        </div>
      </div>
    </div>
  );
}
