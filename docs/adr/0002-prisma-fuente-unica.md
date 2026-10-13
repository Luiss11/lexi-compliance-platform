# ADR-0002 · Prisma como fuente única del esquema

**Estado:** Aceptado

**Contexto:** La web (TypeScript) y la API (Python) usan la misma base PostgreSQL.

**Decisión:** Las migraciones se escriben solo con Prisma en `apps/web/prisma`. La API mapea las mismas tablas con SQLAlchemy y nunca crea ni altera tablas.

**Consecuencias:** Un cambio de modelo requiere PR en `prisma/schema.prisma` y actualizar `services/api/app/models`.
