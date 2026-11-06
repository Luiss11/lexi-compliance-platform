"use client";

import { useFormState, useFormStatus } from "react-dom";
import { changePasswordAction, type PasswordState } from "./actions";

const S0: PasswordState = { ok: null, error: null };
const INPUT = "min-h-11 w-full rounded-md border border-line bg-white px-3 text-sm";

function Submit() {
  const { pending } = useFormStatus();
  return (
    <button type="submit" disabled={pending} className="min-h-11 rounded-md bg-lexi px-5 text-sm font-medium text-white disabled:opacity-60">
      {pending ? "Guardando…" : "Cambiar contraseña"}
    </button>
  );
}

export function PasswordForm() {
  const [state, action] = useFormState(changePasswordAction, S0);
  return (
    <form action={action} className="flex max-w-md flex-col gap-3 rounded-lg border border-line bg-white p-4">
      <label className="flex flex-col gap-1 text-sm">
        Contraseña actual
        <input name="current_password" type="password" required autoComplete="current-password" className={INPUT} />
      </label>
      <label className="flex flex-col gap-1 text-sm">
        Nueva contraseña
        <input name="new_password" type="password" required minLength={10} autoComplete="new-password" className={INPUT} />
        <span className="text-xs text-muted">Mínimo 10 caracteres, con letras y números.</span>
      </label>
      <label className="flex flex-col gap-1 text-sm">
        Repite la nueva contraseña
        <input name="confirm" type="password" required minLength={10} autoComplete="new-password" className={INPUT} />
      </label>
      <Submit />
      {state.error && (
        <p role="alert" className="text-sm text-[#9A2D20]">
          {state.error}
        </p>
      )}
      {state.ok && (
        <p role="status" className="text-sm text-lexi">
          {state.ok}
        </p>
      )}
    </form>
  );
}
