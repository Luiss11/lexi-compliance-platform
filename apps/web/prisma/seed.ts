import { PrismaClient, Priority, Role, TaskStatus } from "@prisma/client";

const prisma = new PrismaClient();

// bcrypt (cost 10) de la contraseña de desarrollo "lexi1234".
// La API verifica con bcrypt, así que el seed debe guardar el mismo formato.
// Solo para desarrollo: en producción cada usuario se crea con su propia contraseña.
const DEV_PASSWORD_HASH = "$2b$10$sjrwq9b8mlVq4zoRnycIZ.RfSHmMuhr5UbpSEY7DMdulSXijC.DZa";

function daysFromNow(days: number): Date {
  const d = new Date();
  d.setUTCHours(0, 0, 0, 0);
  d.setUTCDate(d.getUTCDate() + days);
  return d;
}

async function main() {
  const tenant = await prisma.tenant.upsert({
    where: { slug: "clinica-sonrisa" },
    update: {},
    create: { name: "Clínica Dental Sonrisa (demo)", slug: "clinica-sonrisa", sector: "clinica" },
  });

  const users: [string, string, Role][] = [
    ["Admin Demo", "admin@demo.lexi", Role.ADMIN],
    ["Compliance Demo", "compliance@demo.lexi", Role.COMPLIANCE],
    ["Operator Demo", "operator@demo.lexi", Role.OPERATOR],
  ];

  const byEmail: Record<string, string> = {};
  for (const [name, email, role] of users) {
    const user = await prisma.user.upsert({
      where: { tenantId_email: { tenantId: tenant.id, email } },
      // update reemplaza el hash viejo (SHA-256) de la primera corrida del seed
      update: { name, role, passwordHash: DEV_PASSWORD_HASH },
      create: { tenantId: tenant.id, name, email, role, passwordHash: DEV_PASSWORD_HASH },
    });
    byEmail[email] = user.id;
  }

  // Tareas de ejemplo para que el tablero no se vea vacío. Se crean una sola vez:
  // si ya existen (mismo código) no se tocan, así tus cambios en el tablero se conservan.
  const tasks: {
    code: string;
    title: string;
    status: TaskStatus;
    priority: Priority;
    due: number | null;
    assignee: string | null;
    citation: string | null;
  }[] = [
    { code: "TSK-001", title: "Publicar el aviso de privacidad integral", status: "BACKLOG", priority: "ALTA", due: 10, assignee: "operator@demo.lexi", citation: "LFPDPPP Art. 16" },
    { code: "TSK-002", title: "Firmar cartas de confidencialidad con el personal", status: "IN_PROGRESS", priority: "MEDIA", due: 20, assignee: "operator@demo.lexi", citation: "LFPDPPP Art. 21" },
    { code: "TSK-003", title: "Actualizar el expediente clínico (NOM-004)", status: "IN_REVIEW", priority: "ALTA", due: -3, assignee: "operator@demo.lexi", citation: "NOM-004-SSA3-2012" },
    { code: "TSK-004", title: "Renovar el aviso de funcionamiento", status: "BACKLOG", priority: "BAJA", due: 45, assignee: null, citation: null },
    { code: "TSK-005", title: "Capacitación anual de protección de datos", status: "DONE", priority: "MEDIA", due: -15, assignee: "compliance@demo.lexi", citation: null },
  ];

  for (const t of tasks) {
    await prisma.task.upsert({
      where: { tenantId_code: { tenantId: tenant.id, code: t.code } },
      update: {},
      create: {
        tenantId: tenant.id,
        code: t.code,
        title: t.title,
        status: t.status,
        priority: t.priority,
        dueDate: t.due === null ? null : daysFromNow(t.due),
        assigneeId: t.assignee ? byEmail[t.assignee] : null,
        citation: t.citation,
      },
    });
  }

  console.log("Seed listo: usuarios *@demo.lexi / lexi1234 y 5 tareas de ejemplo");
}

main().finally(() => prisma.$disconnect());
