"use client";

import { useFormState, useFormStatus } from "react-dom";
import { ROLE_NAME, ROLE_OPTIONS, type ManagedUser } from "@/types/users";
import {
  createUserAction,
  resetPasswordAction,
  updateUserAction,
  type FormState,
} from "./actions";

const S0: FormState = { ok: null, error: null };

function Msg({ state }: { state: FormState }) {
  if (state.error)
    return (
      <p role="alert" className="text-sm text-danger">
        {state.error}
      </p>
    );
  if (state.ok)
    return (
      <p role="status" className="text-sm text-lexi">
        {state.ok}
      </p>
    );
  return null;
}

function Button({ children, tone = "primary" }: { children: React.ReactNode; tone?: "primary" | "plain" }) {
  const { pending } = useFormStatus();
  const style =
    tone === "primary"
      ? "bg-lexi text-white"
      : "border border-line bg-white hover:bg-paper";
  return (
    <button type="submit" disabled={pending} className={`min-h-11 rounded-md px-4 text-sm font-medium disabled:opacity-60 ${style}`}>
      {pending ? "Guardando…" : children}
    </button>
  );
}

const INPUT = "min-h-11 w-full rounded-md border border-line bg-white px-3 text-sm";

function CreateForm() {
  const [state, action] = useFormState(createUserAction, S0);
  return (
    <form action={action} className="flex flex-col gap-3 rounded-lg border border-line bg-white p-4">
      <h2 className="font-medium">Agregar usuario</h2>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="flex flex-col gap-1 text-sm">
          Nombre completo
          <input name="full_name" required minLength={2} maxLength={120} autoComplete="off" className={INPUT} />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Correo
          <input name="email" type="email" required autoComplete="off" className={INPUT} />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Rol
          <select name="role" defaultValue="OPERATOR" className={INPUT}>
            {ROLE_OPTIONS.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label} — {r.help}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Contraseña inicial
          <input name="password" type="password" required minLength={10} autoComplete="new-password" className={INPUT} />
          <span className="text-xs text-muted">Mínimo 10 caracteres, con letras y números.</span>
        </label>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <Button>Crear usuario</Button>
        <Msg state={state} />
      </div>
    </form>
  );
}

function UserRow({ user, isMe }: { user: ManagedUser; isMe: boolean }) {
  const [updated, update] = useFormState(updateUserAction, S0);
  const [reset, resetAction] = useFormState(resetPasswordAction, S0);

  return (
    <li className={`flex flex-col gap-3 rounded-lg border border-line bg-white p-4 ${user.active ? "" : "opacity-70"}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="min-w-0">
          <div className="font-medium">
            {user.full_name}
            {isMe && <span className="ml-2 rounded bg-lexi-soft px-2 py-0.5 text-xs text-lexi">Tú</span>}
            {!user.active && <span className="ml-2 rounded bg-danger-soft px-2 py-0.5 text-xs text-danger">Desactivado</span>}
          </div>
          <div className="truncate text-sm text-muted">{user.email}</div>
        </div>
        <span className="text-sm">{ROLE_NAME[user.role]}</span>
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <form action={update} className="flex flex-wrap items-end gap-2">
          <input type="hidden" name="id" value={user.id} />
          <label className="flex flex-col gap-1 text-xs text-muted">
            Cambiar rol
            <select name="role" defaultValue={user.role} disabled={isMe} className="min-h-11 rounded-md border border-line bg-white px-2 text-sm text-ink disabled:opacity-60">
              {ROLE_OPTIONS.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </select>
          </label>
          {!isMe && <Button tone="plain">Guardar rol</Button>}
        </form>

        {!isMe && (
          <form action={update}>
            <input type="hidden" name="id" value={user.id} />
            <input type="hidden" name="active" value={user.active ? "false" : "true"} />
            <Button tone="plain">{user.active ? "Desactivar" : "Reactivar"}</Button>
          </form>
        )}

        {!isMe && (
          <form action={resetAction} className="flex flex-wrap items-end gap-2">
            <input type="hidden" name="id" value={user.id} />
            <label className="flex flex-col gap-1 text-xs text-muted">
              Nueva contraseña
              <input name="new_password" type="password" required minLength={10} autoComplete="new-password" className="min-h-11 rounded-md border border-line bg-white px-2 text-sm text-ink" />
            </label>
            <Button tone="plain">Restablecer</Button>
          </form>
        )}
      </div>
      <Msg state={updated} />
      <Msg state={reset} />
    </li>
  );
}

export function UsersPanel({ users, meId }: { users: ManagedUser[]; meId: string }) {
  return (
    <div className="flex flex-col gap-5">
      <CreateForm />
      <ul className="flex flex-col gap-3">
        {users.map((u) => (
          <UserRow key={u.id} user={u} isMe={u.id === meId} />
        ))}
      </ul>
      <p className="text-xs text-muted">
        Tu propio rol y tu propia cuenta no se pueden cambiar aquí, para que la organización nunca se quede sin administrador.
        Tu contraseña la cambias en «Mi cuenta».
      </p>
    </div>
  );
}
