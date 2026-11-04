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
    # #245: ninguna palabra en español empieza por «rr»; el celular escribe «no rrespira».
    return " ".join(p[1:] if p.startswith("rr") else p for p in sin_tildes.split())
