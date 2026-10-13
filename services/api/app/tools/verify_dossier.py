"""Verifica el sello de un expediente descargado, sin necesitar la API ni la base de datos.

    python -m app.tools.verify_dossier expediente-lexi-2026-10-13.json

Termina con código 0 si el sello coincide y 1 si el expediente fue modificado.
Solo usa la librería estándar: un auditor externo puede copiar este archivo y ejecutarlo.
"""
import hashlib
import json
import sys


def seal_of(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify(data: dict) -> bool:
    claimed = data.get("seal")
    body = {k: v for k, v in data.items() if k != "seal"}
    return bool(claimed) and seal_of(body) == claimed


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Uso: python -m app.tools.verify_dossier <expediente.json>")
        return 2
    with open(argv[1], encoding="utf-8") as fh:
        data = json.load(fh)
    if verify(data):
        print(f"OK: el sello coincide ({data['seal']}).")
        failures = data.get("summary", {}).get("integrity_failures", 0)
        if failures:
            print(f"Aviso: el expediente registra {failures} evidencia(s) con fallas de integridad.")
        return 0
    print("ALTERADO: el contenido ya no coincide con el sello.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
