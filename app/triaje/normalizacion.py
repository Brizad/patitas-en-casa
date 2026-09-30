"""Normalización del texto ciudadano antes del triaje (corrige BUG-01)."""
import unicodedata


def normalizar(texto: str) -> str:
    """Pasa a minúsculas, elimina tildes y compacta espacios.

    'Convulsión  y VÓMITO' -> 'convulsion y vomito'
    """
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFD", texto.lower())
        if unicodedata.category(c) != "Mn"
    )
    return " ".join(sin_tildes.split())
