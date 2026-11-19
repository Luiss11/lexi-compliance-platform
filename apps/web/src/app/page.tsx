import type { Metadata } from "next";
import Link from "next/link";
import { AssistantPreview, EvidencePreview, GapsPreview, PanelPreview } from "@/components/landing/Previews";

// Página pública. Quien ya inició sesión no la ve: el middleware lo manda a /panel.

export const metadata: Metadata = {
  title: "Lexi Compliance · Cumplimiento legal en orden para tu negocio",
  description:
    "Lexi organiza las obligaciones legales de tu PYME: tareas con responsable y fecha, evidencia sellada con SHA-256 y expediente de auditoría listo para la inspección.",
};

const DEMO_MAIL =
  "mailto:luis.simental.isw@unipolidgo.edu.mx?subject=" +
  encodeURIComponent("Quiero una demo de Lexi Compliance") +
  "&body=" +
  encodeURIComponent("Hola, me interesa Lexi para mi negocio.\n\nNombre del negocio:\nGiro:\nCiudad:\n");

const STEPS = [
  {
    title: "Elige tu giro",
    text: "Lexi te propone las obligaciones que suelen aplicar a tu sector, cada una con su norma y su artículo.",
  },
  {
    title: "Asigna tareas",
    text: "Cada obligación se vuelve una tarea con responsable, prioridad y fecha límite.",
  },
  {
    title: "Sube la evidencia",
    text: "Fotos o PDF, incluso desde el celular. Cada archivo queda sellado con su huella SHA‑256.",
  },
  {
    title: "Genera el expediente",
    text: "Un reporte de auditoría listo para imprimir que comprueba que ninguna evidencia se alteró.",
  },
];

const AUDIENCE = [
  {
    who: "Clínicas y consultorios",
    what: "COFEPRIS, expediente clínico, aviso de privacidad y protección civil.",
  },
  {
    who: "Comercios y talleres",
    what: "Protección Civil, normas de seguridad de la STPS, licencias y permisos.",
  },
  {
    who: "Despachos y consultores",
    what: "Cada cliente en su propia organización, con sus datos separados.",
  },
];

const SECURITY = [
  { title: "Conexión cifrada", text: "Todo viaja por HTTPS, de tu navegador al servidor." },
  { title: "Cada negocio aislado", text: "Una organización nunca ve los datos de otra." },
  {
    title: "Permisos por rol",
    text: "Administrador, oficial de cumplimiento y operador ven solo lo que les toca.",
  },
  {
    title: "Respaldos diarios verificados",
    text: "Copia nocturna de datos y evidencias, con prueba de que se pueden restaurar.",
  },
  { title: "Bitácora de auditoría", text: "Queda registro de quién hizo qué y cuándo." },
  {
    title: "IA que cita sus fuentes",
    text: "Si el asistente no encuentra sustento en la normativa, lo dice en lugar de inventar.",
  },
];

function Logo({ light = false }: { light?: boolean }) {
  return (
    <span className="flex items-center gap-2.5">
      <span className="flex h-9 w-9 items-center justify-center rounded-md bg-lexi font-serif text-lg font-semibold text-white">
        L
      </span>
      <span className={`font-serif text-lg font-semibold ${light ? "text-ink-fg" : "text-ink"}`}>
        Lexi Compliance
      </span>
    </span>
  );
}

function Feature({
  title,
  text,
  preview,
  flip = false,
}: {
  title: string;
  text: string;
  preview: React.ReactNode;
  flip?: boolean;
}) {
  return (
    <div className="grid items-center gap-10 lg:grid-cols-2 lg:gap-16">
      <div className={flip ? "lg:order-2" : ""}>
        <h3 className="text-balance font-serif text-3xl font-medium leading-tight sm:text-4xl">{title}</h3>
        <p className="mt-4 max-w-md text-lg leading-relaxed text-muted">{text}</p>
      </div>
      <div className={flip ? "lg:order-1" : ""}>{preview}</div>
    </div>
  );
}

export default function LandingPage() {
  return (
    <div className="bg-paper text-ink">
      {/* Encabezado + portada sobre el mismo fondo oscuro que la pantalla de inicio de sesión */}
      <div className="bg-ink text-ink-fg">
        <header className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-5 sm:px-6">
          <Logo light />
          <nav aria-label="Secciones" className="hidden items-center gap-8 text-sm text-ink-dim md:flex">
            <a href="#como-funciona" className="hover:text-white">Cómo funciona</a>
            <a href="#seguridad" className="hover:text-white">Seguridad</a>
            <a href="#piloto" className="hover:text-white">Plan piloto</a>
          </nav>
          <Link
            href="/login"
            className="flex min-h-11 items-center rounded-md border border-ink-line px-4 text-sm font-medium text-white hover:bg-ink-soft"
          >
            Iniciar sesión
          </Link>
        </header>

        <section className="mx-auto grid max-w-6xl items-center gap-14 px-4 pb-20 pt-12 sm:px-6 lg:grid-cols-[1.05fr_1fr] lg:pb-28 lg:pt-20">
          <div>
            <h1 className="text-balance font-serif text-4xl font-medium leading-[1.08] tracking-tight sm:text-5xl lg:text-6xl">
              Que la próxima inspección te encuentre en orden.
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-relaxed text-ink-dim">
              Lexi reúne las obligaciones legales de tu negocio en un solo lugar: qué te toca cumplir,
              quién se encarga y para cuándo. Guarda la evidencia sellada y arma el expediente de
              auditoría cuando lo necesitas.
            </p>
            <div className="mt-9 flex flex-wrap gap-3">
              <a
                href={DEMO_MAIL}
                className="flex min-h-12 items-center rounded-md bg-lexi px-6 font-semibold text-white transition-colors hover:bg-lexi-bright"
              >
                Solicitar una demo
              </a>
              <a
                href="#como-funciona"
                className="flex min-h-12 items-center rounded-md px-2 font-medium text-ink-fg underline sm:px-5 decoration-ink-line underline-offset-4 hover:decoration-ink-fg"
              >
                Ver cómo funciona
              </a>
            </div>
            <p className="mt-8 max-w-md text-sm text-ink-faint">
              Para clínicas, consultorios, comercios y despachos que no tienen un área legal propia.
            </p>
          </div>
          <div className="lexi-rise">
            <PanelPreview />
          </div>
        </section>
      </div>

      <main>
        {/* El problema, en una frase */}
        <section className="mx-auto max-w-4xl px-4 py-20 text-center sm:px-6 lg:py-28">
          <h2 className="text-balance font-serif text-3xl font-medium leading-tight sm:text-4xl">
            En una PYME, el cumplimiento suele vivir en carpetas, correos y la memoria de alguien.
          </h2>
          <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-muted">
            Cuando llega la revisión de COFEPRIS, Protección Civil o la STPS, el problema rara vez es no
            haber cumplido. Es no poder demostrarlo a tiempo.
          </p>
        </section>

        <section id="como-funciona" className="scroll-mt-6 border-y border-line bg-white">
          <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6 lg:py-24">
            <h2 className="max-w-2xl text-balance font-serif text-3xl font-medium leading-tight sm:text-4xl">
              Del reglamento a la evidencia, en cuatro pasos
            </h2>
            <ol className="mt-14 grid gap-10 sm:grid-cols-2 lg:grid-cols-4 lg:gap-8">
              {STEPS.map((s, i) => (
                <li key={s.title} className="border-t-2 border-ink pt-5">
                  <span className="font-mono text-sm text-lexi">Paso {i + 1}</span>
                  <h3 className="mt-2 font-serif text-xl font-semibold">{s.title}</h3>
                  <p className="mt-2 leading-relaxed text-muted">{s.text}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section aria-label="Funciones" className="mx-auto flex max-w-6xl flex-col gap-24 px-4 py-24 sm:px-6 lg:gap-32 lg:py-32">
          <Feature
            title="Pregunta en español y recibe la respuesta con su cita"
            text="El asistente busca en la normativa que cargaste y responde señalando el documento que la respalda. Si no encuentra sustento, te lo dice en lugar de inventar."
            preview={<AssistantPreview />}
          />
          <Feature
            flip
            title="Encuentra lo que te falta antes que el inspector"
            text="Lexi compara lo que suele exigirse a tu giro con las tareas que ya tienes y te sugiere las obligaciones que nadie está atendiendo."
            preview={<GapsPreview />}
          />
          <Feature
            title="Evidencia que no se puede maquillar"
            text="Al subir un archivo se calcula su huella SHA‑256. Si alguien lo cambia después, el expediente de auditoría lo marca como alterado."
            preview={<EvidencePreview />}
          />
        </section>

        <section className="border-t border-line">
          <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6 lg:py-24">
            <h2 className="max-w-2xl text-balance font-serif text-3xl font-medium leading-tight sm:text-4xl">
              Hecho para negocios sin área legal
            </h2>
            <dl className="mt-12 grid gap-x-10 gap-y-8 md:grid-cols-3">
              {AUDIENCE.map((a) => (
                <div key={a.who}>
                  <dt className="font-serif text-xl font-semibold">{a.who}</dt>
                  <dd className="mt-2 leading-relaxed text-muted">{a.what}</dd>
                </div>
              ))}
            </dl>
          </div>
        </section>

        <section id="seguridad" className="scroll-mt-6 bg-ink text-ink-fg">
          <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6 lg:py-24">
            <h2 className="max-w-2xl text-balance font-serif text-3xl font-medium leading-tight sm:text-4xl">
              Tus datos, cuidados como evidencia
            </h2>
            <ul className="mt-12 grid gap-x-12 gap-y-9 sm:grid-cols-2 lg:grid-cols-3">
              {SECURITY.map((s) => (
                <li key={s.title} className="border-l border-ink-line pl-5">
                  <h3 className="font-semibold text-white">{s.title}</h3>
                  <p className="mt-1.5 leading-relaxed text-ink-dim">{s.text}</p>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section id="piloto" className="scroll-mt-6">
          <div className="mx-auto max-w-3xl px-4 py-24 text-center sm:px-6 lg:py-32">
            <h2 className="text-balance font-serif text-3xl font-medium leading-tight sm:text-5xl">
              Buscamos las primeras PYMEs para un plan piloto
            </h2>
            <p className="mx-auto mt-6 max-w-xl text-lg leading-relaxed text-muted">
              Sin costo durante el piloto. Te ayudamos a cargar tus obligaciones y tú nos cuentas qué te
              sirve y qué no.
            </p>
            <div className="mt-10 flex flex-wrap justify-center gap-3">
              <a
                href={DEMO_MAIL}
                className="flex min-h-12 items-center rounded-md bg-lexi px-7 font-semibold text-white transition-colors hover:bg-lexi-dark"
              >
                Solicitar una demo
              </a>
              <Link
                href="/login"
                className="flex min-h-12 items-center rounded-md border border-line-strong bg-white px-6 font-medium hover:bg-paper-soft"
              >
                Ya tengo cuenta
              </Link>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-10 text-sm text-muted sm:px-6 md:flex-row md:items-start md:justify-between">
          <div className="max-w-md">
            <Logo />
            <p className="mt-4 leading-relaxed">
              Lexi es una herramienta para organizar el cumplimiento; no sustituye la asesoría de un
              abogado.
            </p>
          </div>
          <div className="leading-relaxed md:max-w-md md:text-right">
            <p>Proyecto académico, 2026.</p>
            <p className="mt-1 text-pretty">
              Luis Simental, Jonathan García, Yubel Regalado y Yosvanni&nbsp;Bañuelos.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
