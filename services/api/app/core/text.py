"""Utilidades de texto."""


def fix_mojibake(text: str) -> str:
    """Repara nombres de archivo con acentos rotos («quÃ©» -> «qué»).

    Pasa cuando el UTF-8 del navegador se lee como Latin-1 en algún punto del camino. Solo
    cambia el texto si al revertirlo queda UTF-8 válido, así que un nombre normal («Ñandú»,
    «Informe café») no se toca.
    """
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text
