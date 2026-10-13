"""Agente Supervisor / Mejora Continua (TASK-10).

Tres capacidades:
1. audit_gaps: compara los documentos del tenant contra los requeridos por su sector.
2. suggest_tasks: convierte un fragmento legal en tareas con prioridad y fecha.
3. review_evidence: opina si una evidencia es formalmente válida antes de la auditoría.
"""
from dataclasses import dataclass

# Catálogo mínimo por sector; QA (TASK-06) lo amplía con la matriz normativa.
SECTOR_REQUIREMENTS: dict[str, list[str]] = {
    "clinica": [
        "Programa Interno de Protección Civil",
        "Licencia sanitaria",
        "Aviso de privacidad",
        "Contrato de recolección RPBI",
    ],
    "restaurante": [
        "Programa Interno de Protección Civil",
        "Aviso de funcionamiento",
        "Manual de higiene (NOM-251)",
    ],
}


@dataclass
class Gap:
    requirement: str
    severity: str  # ALTA | MEDIA | AVISO
    reason: str


def audit_gaps(sector: str, document_titles: list[str]) -> list[Gap]:
    titles = " ".join(document_titles).lower()
    gaps: list[Gap] = []
    for req in SECTOR_REQUIREMENTS.get(sector, []):
        keyword = req.lower().split(" (")[0]
        if keyword not in titles:
            gaps.append(Gap(req, "ALTA", "No se encontró un documento equivalente cargado."))
    return gaps


async def suggest_tasks(tenant_id: str, citation_text: str) -> list[dict]:
    """TODO(Yubel): prompt al LLM con salida JSON validada contra schemas.tasks.TaskSuggestion."""
    raise NotImplementedError


async def review_evidence(task_requirement: str, evidence_text: str) -> str:
    """TODO(Yubel): devuelve 'válida', 'casi válida: <faltante>' o 'no válida: <motivo>'."""
    raise NotImplementedError
