import { PrismaClient, Role } from "@prisma/client";

const prisma = new PrismaClient();

// bcrypt (cost 10) de la contraseña de desarrollo "lexi1234".
// La API verifica con bcrypt, así que el seed debe guardar el mismo formato.
// Solo para desarrollo: en producción cada usuario se crea con su propia contraseña.
const DEV_PASSWORD_HASH = "$2b$10$sjrwq9b8mlVq4zoRnycIZ.RfSHmMuhr5UbpSEY7DMdulSXijC.DZa";

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

  for (const [name, email, role] of users) {
    await prisma.user.upsert({
      where: { tenantId_email: { tenantId: tenant.id, email } },
      // update reemplaza el hash viejo (SHA-256) de la primera corrida del seed
      update: { name, role, passwordHash: DEV_PASSWORD_HASH },
      create: { tenantId: tenant.id, name, email, role, passwordHash: DEV_PASSWORD_HASH },
    });
  }
  console.log("Seed listo: usuarios *@demo.lexi / lexi1234");
}

main().finally(() => prisma.$disconnect());
