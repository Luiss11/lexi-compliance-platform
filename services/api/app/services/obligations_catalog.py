"""Catálogo de obligaciones por sector (clínica, comercio y las comunes a todos).

Los datos viven en app/data/obligations.json. Cada obligación indica su norma, el numeral o
artículo, y si su texto se leyó en fuente oficial (verificado), en un sitio no oficial (parcial)
o si todavía falta (pendiente). No es asesoría legal.
"""
import json
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "obligations.json"

# El sector del tenant es texto libre («clinica», «Clínica dental», «retail»…): se reconoce por
# palabras clave, sin acentos ni mayúsculas.
SECTOR_KEYWORDS = {
    "clinica": ("clinic", "dental", "dentist", "odontolog", "consultorio", "medic", "salud"),
    "comercio": ("comerc", "retail", "tienda", "abarrote", "venta"),
}

Estado = Literal["verificado", "parcial", "pendiente"]


class Obligation(BaseModel):
    id: str
    sector: Literal["todos", "clinica", "comercio"]
    norma: str
    norma_titulo: str
    publicacion: str
    cita: str
    titulo: str
    obligacion: str
    frecuencia: Literal[
        "una_vez", "anual", "mensual", "cada_2_meses", "continua", "por_evento"
    ]
    evidencia_sugerida: str
    cita_textual: str | None = None
    estado_verificacion: Estado
    nota: str | None = None


class Pending(BaseModel):
    tema: str
    sector: Literal["todos", "clinica", "comercio"]
    motivo: str


class Catalog(BaseModel):
    version: str
    aviso: str
    sectores: list[str]
    obligaciones: list[Obligation]
    pendientes: list[Pending]


@lru_cache
def load_catalog() -> Catalog:
    return Catalog.model_validate(json.loads(DATA_FILE.read_text(encoding="utf-8")))


def normalize_sector(sector: str | None) -> str | None:
    plain = "".join(
        c for c in unicodedata.normalize("NFKD", (sector or "").casefold())
        if not unicodedata.combining(c)
    )
    for key, words in SECTOR_KEYWORDS.items():
        if any(w in plain for w in words):
            return key
    return None


def for_sector(sector: str | None) -> list[Obligation]:
    """Obligaciones comunes más las del sector. Un sector desconocido recibe solo las comunes."""
    wanted = {"todos"}
    normalized = normalize_sector(sector)
    if normalized:
        wanted.add(normalized)
    return [o for o in load_catalog().obligaciones if o.sector in wanted]
