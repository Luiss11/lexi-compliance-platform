"""Ingesta de PDFs con PyMuPDF preservando página y cláusula (TASK-08)."""
import re
from dataclasses import dataclass

import fitz  # PyMuPDF

CLAUSE_RE = re.compile(
    r"^\s*(Art[íi]culo\s+\d+[A-Za-z]?|Art\.\s*\d+|Cl[áa]usula\s+\w+|\d+(\.\d+)+)",
    re.IGNORECASE,
)


@dataclass
class PageBlock:
    page: int
    clause: str | None
    text: str


def parse_pdf(path: str) -> list[PageBlock]:
    """Devuelve bloques de texto con su número de página (1-based) y la cláusula vigente."""
    blocks: list[PageBlock] = []
    current_clause: str | None = None
    with fitz.open(path) as doc:
        for page_index, page in enumerate(doc, start=1):
            for *_, text, _, _ in page.get_text("blocks"):
                text = text.strip()
                if not text:
                    continue
                match = CLAUSE_RE.match(text)
                if match:
                    current_clause = match.group(1).strip()
                blocks.append(PageBlock(page=page_index, clause=current_clause, text=text))
    return blocks


def has_text_layer(path: str) -> bool:
    """Detecta PDFs escaneados sin texto (requieren OCR)."""
    with fitz.open(path) as doc:
        return any(page.get_text().strip() for page in doc)
