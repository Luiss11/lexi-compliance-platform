# Diseño

Mockups de las pantallas (lienzo de diseño):
00 Inicio de sesión · 01 Panel de cumplimiento · 02 Asistente legal RAG · 03 Biblioteca de documentos · 04 Tablero de tareas · 05 Evidencia móvil (Operator).

## Tokens

Fuente única: `apps/web/tailwind.config.ts`. No uses hex sueltos en los componentes (`bg-[#…]`); si falta un tono, añádelo allí y aquí.

| Token | Valor | Uso |
|---|---|---|
| paper / soft / deep | `#F5F4EF` / `#FAF9F5` / `#ECEAE2` | Fondo · barras fijas · pistas, columnas y etiquetas neutras |
| ink | `#15171C` | Texto y barra lateral |
| ink-fg / dim / faint | `#E9E7E0` / `#C9CCD3` / `#A9ADB6` | Texto sobre la barra lateral, de más a menos énfasis |
| ink-active / raised | `#2A2E36` / `#3B4049` | Elemento activo y avatar en la barra lateral |
| muted | `#555B66` | Texto secundario |
| line / strong | `#DEDBD2` / `#C9C5B9` | Bordes · bordes de campos de formulario |

Tonos de estado. Todos tienen la misma forma: `DEFAULT` para texto, `soft` para fondo, `line` para borde de aviso y `bright` para puntos, barras y gráficos (nunca texto pequeño).

| Tono | DEFAULT | soft | line | bright | Uso |
|---|---|---|---|---|---|
| lexi | `#0E5A55` | `#E6F1EF` | `#B7D6D2` | `#1F7A68` | Acción principal, cumplido, éxito |
| warn | `#7A5600` | `#FFF3D6` | `#EAD7A5` | `#C98A12` | Atención, prioridad media, en curso |
| danger | `#9A2D20` | `#FBE9E7` | `#E7B8B1` | `#B3372A` | Vencido, error, prioridad alta |
| info | `#3F4B66` | `#EEF0F5` | `#CDD3E0` | `#5B6B7A` | Sugerencias de IA, en revisión |

Tipografía: IBM Plex Serif (títulos), IBM Plex Sans (texto), IBM Plex Mono (citas y hashes).
