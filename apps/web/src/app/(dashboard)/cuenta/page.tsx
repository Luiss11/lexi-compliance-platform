import { getSession } from "@/lib/session";
import { ROLE_NAME } from "@/types/users";
import { PasswordForm } from "./PasswordForm";

export default async function CuentaPage() {
  const me = await getSession();
  return (
    <div className="flex max-w-4xl flex-col gap-6">
      <header>
        <h1 className="font-serif text-3xl font-semibold">Mi cuenta</h1>
        {me && (
          <p className="mt-2 text-sm text-muted">
            {me.user.full_name} · {me.user.email} · {ROLE_NAME[me.user.role]} · {me.tenant.name}
          </p>
        )}
      </header>
      <PasswordForm />
    </div>
  );
}
