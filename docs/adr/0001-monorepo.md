# ADR-0001 · Monorepo con apps/ y services/

**Estado:** Aceptado

**Contexto:** Equipo de 4 personas, un solo repositorio oficial (`Luiss11/lexi-compliance-platform`) y entregas semanales.

**Decisión:** Un monorepo con `apps/web` (Next.js) y `services/api` (FastAPI), orquestados con `docker-compose`.

**Consecuencias:** Un solo tablero, un solo CI y versiones sincronizadas para cada demo. El CI corre por carpeta para no reconstruir todo.
