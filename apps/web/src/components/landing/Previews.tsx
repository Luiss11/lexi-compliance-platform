// Vistas del producto dibujadas con los mismos tokens que la app (no son capturas):
// se ven nítidas en cualquier pantalla y siguen el estilo real si cambia la paleta.
// Los datos son de demostración y así se rotulan en la página.

function Ring({ value }: { value: number }) {
  const r = 26;
  const c = 2 * Math.PI * r;
  return (
    <svg viewBox="0 0 64 64" className="h-16 w-16 shrink-0" aria-hidden>
      <circle cx="32" cy="32" r={r} fill="none" strokeWidth="7" className="stroke-paper-deep" />
      <circle
        cx="32" cy="32" r={r} fill="none" strokeWidth="7" strokeLinecap="round"
        strokeDasharray={`${(c * value) / 100} ${c}`} transform="rotate(-90 32 32)"
        className="stroke-warn-bright"
      />
      <text x="32" y="37" textAnchor="middle" className="fill-ink font-serif" fontSize="16" fontWeight="600">
        {value}
      </text>
    </svg>
  );
}

const PRIORITY = {
  ALTA: "bg-danger-soft text-danger",
  MEDIA: "bg-warn-soft text-warn",
} as const;

export function PanelPreview() {
  return (
    <figure className="w-full">
      <div className="overflow-hidden rounded-xl border border-ink-line/40 bg-paper text-ink shadow-[0_30px_70px_-25px_rgba(0,0,0,0.7)]">
        <div className="flex items-center justify-between border-b border-line bg-white px-4 py-2.5">
          <span className="font-serif text-sm font-semibold">Clínica Dental Sonrisa</span>
          <span className="text-xs text-muted">Panel de cumplimiento</span>
        </div>

        <div className="grid gap-3 p-4 sm:grid-cols-[1.3fr_1fr]">
          <div className="flex items-center gap-3 rounded-lg border border-line bg-white p-3">
            <Ring value={72} />
            <div>
              <div className="text-xs text-muted">Índice de cumplimiento</div>
              <div className="font-serif text-lg font-semibold text-warn">En progreso</div>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-lg border border-line bg-white p-3">
              <div className="text-xs text-muted">Vencidas</div>
              <div className="mt-1 font-serif text-2xl font-semibold text-danger">1</div>
            </div>
            <div className="rounded-lg border border-line bg-white p-3">
              <div className="text-xs text-muted">Con evidencia</div>
              <div className="mt-1 font-serif text-2xl font-semibold">83%</div>
            </div>
          </div>
        </div>

        <div className="mx-4 mb-4 rounded-lg border border-line bg-white">
          <div className="border-b border-line px-3 py-2 text-xs font-semibold">Próximos vencimientos</div>
          <ul className="divide-y divide-line text-sm">
            {[
              { code: "TSK-004", title: "Actualizar el aviso de privacidad", when: "Vence en 3 días", p: "ALTA" as const },
              { code: "TSK-007", title: "Simulacro de evacuación", when: "Vence en 12 días", p: "MEDIA" as const },
              { code: "TSK-009", title: "Bitácora de esterilización", when: "Vence en 14 días", p: "ALTA" as const },
            ].map((t) => (
              <li key={t.code} className="flex items-center justify-between gap-3 px-3 py-2">
                <div className="min-w-0">
                  <div className="truncate">
                    <span className="font-mono text-[11px] text-muted">{t.code}</span> {t.title}
                  </div>
                  <div className="text-xs text-muted">{t.when}</div>
                </div>
                <span className={`shrink-0 rounded px-2 py-0.5 text-[11px] ${PRIORITY[t.p]}`}>{t.p}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
      <figcaption className="mt-3 text-center text-xs text-ink-faint">Datos de demostración</figcaption>
    </figure>
  );
}

export function AssistantPreview() {
  return (
    <div className="rounded-xl border border-line bg-white p-5 shadow-[0_18px_40px_-24px_rgba(21,23,28,0.35)]">
      <p className="ml-auto w-fit max-w-[85%] rounded-2xl rounded-br-md bg-ink px-4 py-2.5 text-sm text-ink-fg">
        ¿Cada cuánto tenemos que hacer simulacros de incendio?
      </p>
      <div className="mt-4 max-w-[92%] rounded-2xl rounded-bl-md bg-paper px-4 py-3 text-sm leading-relaxed">
        Al menos una vez al año si tu centro de trabajo es de riesgo ordinario, y dos veces al año
        si es de riesgo alto. Conserva el registro de cada simulacro como evidencia.
        <div className="mt-3 rounded-md border border-line bg-white px-3 py-2">
          <div className="font-mono text-[11px] text-lexi">NOM-002-STPS-2010</div>
          <div className="text-xs text-muted">Condiciones de seguridad · Prevención y protección contra incendios</div>
        </div>
      </div>
      <p className="mt-4 text-xs text-muted">Respuesta con la cita del documento que la respalda.</p>
    </div>
  );
}

export function GapsPreview() {
  return (
    <div className="rounded-xl border border-line bg-white shadow-[0_18px_40px_-24px_rgba(21,23,28,0.35)]">
      <div className="border-b border-line px-5 py-3 text-sm font-semibold">Obligaciones sin atender</div>
      <ul className="divide-y divide-line">
        {[
          { t: "Programa interno de protección civil", n: "Ley General de Protección Civil", p: "ALTA" as const },
          { t: "Señalización de rutas de evacuación", n: "NOM-003-SEGOB-2011", p: "MEDIA" as const },
        ].map((g) => (
          <li key={g.t} className="flex flex-wrap items-center justify-between gap-3 px-5 py-3.5">
            <div className="min-w-0">
              <div className="text-sm font-medium">{g.t}</div>
              <div className="font-mono text-[11px] text-muted">{g.n}</div>
            </div>
            <div className="flex items-center gap-2">
              <span className={`rounded px-2 py-0.5 text-[11px] ${PRIORITY[g.p]}`}>{g.p}</span>
              <span className="rounded-md border border-lexi px-2.5 py-1 text-xs font-medium text-lexi">
                Agregar como tarea
              </span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function EvidencePreview() {
  const rows = [
    { f: "aviso-privacidad-firmado.pdf", h: "2d6be48e59…c152133fb", ok: true },
    { f: "bitacora-extintores.jpg", h: "7033f1fc4b…0fce3edb062", ok: false },
  ];
  return (
    <div className="rounded-xl border border-line bg-white shadow-[0_18px_40px_-24px_rgba(21,23,28,0.35)]">
      <div className="border-b border-line px-5 py-3 text-sm font-semibold">Verificación de integridad</div>
      <ul className="divide-y divide-line">
        {rows.map((r) => (
          <li key={r.f} className="flex flex-wrap items-center justify-between gap-3 px-5 py-3.5">
            <div className="min-w-0">
              <div className="truncate text-sm">{r.f}</div>
              <div className="font-mono text-[11px] text-muted">SHA-256 {r.h}</div>
            </div>
            <span
              className={`rounded px-2 py-0.5 text-[11px] font-medium ${
                r.ok ? "bg-lexi-soft text-lexi" : "bg-danger-soft text-danger"
              }`}
            >
              {r.ok ? "Íntegra" : "ALTERADA"}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
