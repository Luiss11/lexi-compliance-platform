"use client";

import { useFormState, useFormStatus } from "react-dom";
import { loginAction, type LoginState } from "./actions";

const initialState: LoginState = { error: null };

function SubmitButton() {
  const { pending } = useFormStatus();
  return (
    <button
      type="submit"
      disabled={pending}
      className="h-12 rounded-md bg-lexi font-semibold text-white hover:bg-lexi-dark disabled:opacity-60"
    >
      {pending ? "Entrando…" : "Entrar"}
    </button>
  );
}

export function LoginForm({ demoHint }: { demoHint: boolean }) {
  const [state, formAction] = useFormState(loginAction, initialState);

  return (
    <form action={formAction} className="flex w-full max-w-sm flex-col gap-5">
      <h2 className="font-serif text-3xl font-semibold">Iniciar sesión</h2>

      {state.error && (
        <p role="alert" className="rounded-md bg-danger-soft px-3 py-2.5 text-sm text-danger">
          {state.error}
        </p>
      )}

      <label className="flex flex-col gap-1.5 text-sm font-medium">
        Organización
        <input
          name="tenant"
          defaultValue="clinica-sonrisa"
          autoComplete="organization"
          required
          className="h-12 rounded-md border border-[#C9C5B9] bg-white px-3 font-normal"
        />
      </label>
      <label className="flex flex-col gap-1.5 text-sm font-medium">
        Correo electrónico
        <input
          name="email"
          type="email"
          autoComplete="username"
          required
          className="h-12 rounded-md border border-[#C9C5B9] bg-white px-3 font-normal"
        />
      </label>
      <label className="flex flex-col gap-1.5 text-sm font-medium">
        Contraseña
        <input
          name="password"
          type="password"
          autoComplete="current-password"
          required
          className="h-12 rounded-md border border-[#C9C5B9] bg-white px-3 font-normal"
        />
      </label>

      <SubmitButton />

      {demoHint && (
        <p className="text-xs leading-relaxed text-muted">
          Desarrollo: admin@demo.lexi, compliance@demo.lexi u operator@demo.lexi con la contraseña
          lexi1234.
        </p>
      )}
    </form>
  );
}
