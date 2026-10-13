import { LoginForm } from "./LoginForm";

export default function LoginPage() {
  return (
    <div className="flex min-h-screen flex-wrap">
      <section className="flex flex-1 basis-[460px] flex-col justify-between gap-12 bg-ink p-14 text-[#E9E7E0]">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-lexi font-serif text-xl font-semibold text-white">
            L
          </div>
          <span className="font-serif text-xl font-semibold">Lexi Compliance</span>
        </div>
        <h1 className="max-w-md font-serif text-5xl font-medium leading-tight">
          Tus obligaciones legales, mapeadas y con evidencia.
        </h1>
        <p className="max-w-md text-sm text-[#A9ADB6]">Conexión TLS 1.3 · JWT · RBAC</p>
      </section>

      <section className="flex flex-1 basis-[420px] items-center justify-center px-6 py-14">
        <LoginForm demoHint={process.env.NODE_ENV !== "production"} />
      </section>
    </div>
  );
}
