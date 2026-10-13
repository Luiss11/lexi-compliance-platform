# Lexi Compliance Platform

Plataforma multi-tenant para que PYMEs (clínicas, comercios) auditen, mapeen y gestionen sus obligaciones legales con un **motor RAG híbrido** y un **Agente Supervisor de IA**.

> Baseline V1.0 · 9B Gestión de Proyectos de Software · Prof. Jose Luis Bautista

## Equipo

| Integrante | Rol | Área en el repo |
|---|---|---|
| Luis Angel Simental Gutierrez | PM & Scrum Master | `.github/`, `docs/` |
| Jonathan Martin Garcia Coronel | BA & Compliance QA Lead | `qa/` |
| Yubel Mitzu Regalado Bailon | AI / RAG & Backend | `services/api/` |
| Yosvanni Bañuelos Flores | Full-Stack & MLOps / Security | `apps/web/`, `docker-compose.yml` |

## Estructura del monorepo

```
lexi-compliance-platform/
├── apps/web/            Next.js 14 (App Router, TS, Tailwind) + Prisma (dueño del esquema)
├── services/api/        FastAPI async: auth RBAC, tareas, evidencias SHA-256, RAG y agente
├── qa/                  Dataset de PDFs normativos y casos TC-AI-HALLUCINATION
├── docs/                Arquitectura, ADRs, convenciones, diseño (mockups)
├── scripts/             Setup y utilidades de desarrollo
├── .github/             Plantillas de issues/PRs y CI
└── docker-compose.yml   Postgres + pgvector, Qdrant, API y Web
```

## Arranque rápido (entorno de desarrollo)

Requisitos: Docker 24+, Node 20 LTS, Python 3.11, Git.

```bash
git clone https://github.com/Luiss11/lexi-compliance-platform.git
cd lexi-compliance-platform
cp .env.example .env          # edita OPENAI_API_KEY y JWT_SECRET
make up                       # levanta postgres, qdrant, api y web
make migrate                  # aplica migraciones Prisma
make seed                     # tenant demo + usuarios por rol
```

| Servicio | URL |
|---|---|
| Web | http://localhost:3000 |
| API + OpenAPI Docs | http://localhost:8000/docs |
| Qdrant dashboard | http://localhost:6333/dashboard |

Desarrollo sin Docker para la app: `make dev-web` y `make dev-api` (ver `Makefile`).

## Documentación

- [Arquitectura](docs/ARCHITECTURE.md)
- [Convenciones de trabajo (ramas, commits, PRs)](docs/CONTRIBUTING.md)
- [Calendario de sprints](docs/SPRINTS.md)
- [Decisiones de arquitectura (ADR)](docs/adr/)
