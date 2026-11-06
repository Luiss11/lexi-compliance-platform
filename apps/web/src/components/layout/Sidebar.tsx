"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { canAccess, type Role } from "@/lib/rbac";
import type { SessionUser } from "@/types/auth";

const NAV = [
  { href: "/panel", label: "Panel" },
  { href: "/asistente", label: "Asistente legal" },
  { href: "/documentos", label: "Documentos" },
  { href: "/tareas", label: "Tareas" },
  { href: "/obligaciones", label: "Obligaciones" },
  { href: "/vacios", label: "Vacíos normativos" },
  { href: "/evidencias", label: "Evidencias" },
  { href: "/expediente", label: "Expediente" },
  { href: "/auditoria", label: "Auditoría" },
  { href: "/usuarios", label: "Usuarios" },
  { href: "/cuenta", label: "Mi cuenta" },
];

const ROLE_LABEL: Record<Role, string> = {
  ADMIN: "Administrador",
  COMPLIANCE: "Oficial de cumplimiento",
  OPERATOR: "Operador",
};

function initials(name: string) {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join("");
}

export function Sidebar({ user, tenantName }: { user: SessionUser; tenantName: string }) {
  const pathname = usePathname();
  const items = NAV.filter((item) => canAccess(item.href, user.role));

  return (
    <nav
      aria-label="Navegación principal"
      className="flex flex-1 basis-[220px] flex-col gap-7 bg-ink px-4 py-6 text-ink-fg"
    >
      <div className="flex items-center gap-2.5 px-2">
        <div className="flex h-9 w-9 items-center justify-center rounded-md bg-lexi font-serif text-lg font-semibold text-white">
          L
        </div>
        <div>
          <div className="font-serif text-lg font-semibold">Lexi</div>
          <div className="text-[11px] tracking-widest text-ink-faint">COMPLIANCE</div>
        </div>
      </div>

      <div className="rounded-md border border-ink-line bg-ink-soft px-3 py-2 text-[13px]">
        <div className="text-[11px] text-ink-faint">Organización</div>
        {tenantName}
      </div>

      <ul className="flex flex-col gap-1">
        {items.map((item) => {
          const active = pathname.startsWith(item.href);
          return (
            <li key={item.href}>
              <Link
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={`flex min-h-11 items-center rounded-md px-3 ${
                  active ? "bg-ink-active font-medium text-white" : "text-ink-dim hover:bg-ink-soft"
                }`}
              >
                {item.label}
              </Link>
            </li>
          );
        })}
      </ul>

      <div className="mt-auto flex flex-col gap-3 border-t border-ink-line px-2 pt-4">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-ink-raised text-[13px] font-semibold">
            {initials(user.full_name)}
          </div>
          <div className="min-w-0 text-[13px]">
            <div className="truncate">{user.full_name}</div>
            <div className="truncate text-xs text-ink-faint">{ROLE_LABEL[user.role]}</div>
          </div>
        </div>
        {/* <a> y no <Link>: Link precarga la ruta y cerraría la sesión sin que hagas clic */}
        <a
          href="/logout"
          className="flex min-h-11 items-center rounded-md px-3 text-sm text-ink-dim hover:bg-ink-soft"
        >
          Cerrar sesión
        </a>
      </div>
    </nav>
  );
}
