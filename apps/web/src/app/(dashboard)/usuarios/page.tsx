import { redirect } from "next/navigation";
import { API_URL, getSession, getToken } from "@/lib/session";
import type { ManagedUser } from "@/types/users";
import { UsersPanel } from "./UsersPanel";

async function fetchUsers(): Promise<ManagedUser[] | null> {
  const token = getToken();
  if (!token) redirect("/logout");
  try {
    const res = await fetch(`${API_URL}/users`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    if (res.status === 401) redirect("/logout");
    if (!res.ok) return null;
    return ((await res.json()) as { items: ManagedUser[] }).items;
  } catch {
    return null;
  }
}

export default async function UsuariosPage() {
  const [users, me] = await Promise.all([fetchUsers(), getSession()]);

  return (
    <div className="flex max-w-4xl flex-col gap-6">
      <header>
        <h1 className="font-serif text-3xl font-semibold">Usuarios</h1>
        <p className="mt-2 text-sm text-muted">
          Quién puede entrar a tu organización y con qué permisos. Desactivar a una persona le quita el acceso sin borrar su
          historial. Los cambios de rol o de acceso se aplican por completo en su próximo inicio de sesión (hasta 1 hora).
        </p>
      </header>

      {users === null ? (
        <div role="alert" className="rounded-md border border-[#E7B8B1] bg-[#FBE9E7] px-4 py-3 text-sm text-[#9A2D20]">
          No se pudo cargar la lista de usuarios. Intenta de nuevo en un momento.
        </div>
      ) : (
        <UsersPanel users={users} meId={me?.user.id ?? ""} />
      )}
    </div>
  );
}
