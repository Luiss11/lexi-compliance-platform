# Convenciones de trabajo

## Ramas (GitFlow simplificado)

- `main`: solo lo que se demuestra el jueves a stakeholders.
- `develop`: integración diaria.
- Ramas de trabajo: `feature/TASK-08-parser-pymupdf`, `fix/TASK-13-rbac-operator`, `docs/...`, `chore/...`.

## Commits (Conventional Commits)

```
feat(rag): preserva número de página en chunks (TASK-08)
fix(auth): Operator no puede borrar documentos (TASK-13)
docs(pm): calendario de sprints
test(qa): casos TC-AI-HALLUCINATION 01-10
```

## Pull Requests

- Siempre hacia `develop`, con la plantilla llena y al menos 1 revisión.
- Cambios en `app/rag/` requieren revisión de QA (Jonathan).
- Merge `develop → main` solo el miércoles, antes de la demo del jueves.

## Tablero GitHub Projects v2

Columnas: **Backlog → Ready → In Progress → In Review/QA → Done**.
Campos personalizados: `Área` (PM, QA, AI/BE, FS/SEC), `Sprint`, `Story points`, `Hito`.

## Ceremonias

| Ceremonia | Cuándo |
|---|---|
| Daily | Lunes a viernes, 8:00–8:15 (dentro de la clase) |
| Trabajo técnico | Lunes, martes, miércoles y viernes, 8:15–9:00 |
| Demo / Sprint Review con stakeholders | Jueves (Regla de Empalme Zero: ese día no hay juntas técnicas) |
| Retrospectiva | Viernes de cierre de sprint |
