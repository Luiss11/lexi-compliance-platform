import { redirect } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";
import { getSession } from "@/lib/session";

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const me = await getSession();

  // Token válido pero la API no reconoce al usuario (o está caída): /logout limpia la
  // cookie. Redirigir a /login directamente haría un bucle, porque el middleware
  // manda de vuelta al panel a quien tiene cookie.
  if (!me) redirect("/logout");

  return (
    <div className="flex min-h-screen flex-wrap print:block">
      {/* El menú no se imprime: el expediente sale limpio en papel o PDF */}
      <div className="flex flex-1 basis-[220px] print:hidden">
        <Sidebar user={me.user} tenantName={me.tenant.name} />
      </div>
      <main className="min-w-0 flex-[999_1_560px] px-10 py-8 print:p-0">{children}</main>
    </div>
  );
}
