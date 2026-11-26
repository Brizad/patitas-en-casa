"""Documentación pública de la API (/docs y /openapi.json) presentada como producto (#464).

Las descripciones de cada ruta salen de los docstrings, que citan los requisitos y los issues del
desarrollo (RF-25, RN-14, DT-02, #422...). Eso sirve en el código, no a quien integra la API: aquí
se quitan esas marcas SOLO del documento publicado. No cambia ninguna ruta, ningún esquema ni la
lógica; los docstrings del código quedan como están.
"""
from __future__ import annotations

import re
from typing import Any

from fastapi import FastAPI

DESCRIPCION = (
    "API de **Patitas en Casa**, la plataforma para atender emergencias animales en Cúcuta: "
    "reporte ciudadano sin cuenta, triaje con inteligencia artificial confirmado por un "
    "veterinario, rescate por comunas, control de cupos del refugio y adopción responsable con "
    "seguimiento. Pensada para refugios, fundaciones y alcaldías.\n\n"
    "Las rutas del personal exigen `Authorization: Bearer` con el token de `POST /auth/token`."
)

_CODIGO = r"(?:(?:RNF|RF|RN|DT|HU|FPI)-\d+[a-z]?|#\d+)"
_LISTA = rf"{_CODIGO}(?:\s*(?:,|;|y|/)\s*{_CODIGO})*"
_PATRONES = [
    (re.compile(rf"\(\s*{_LISTA}\s*\)"), ""),          # «(RN-14)», «(#422, #430)»
    (re.compile(rf"^{_LISTA}\s*:\s*"), ""),          # «RF-25: el coordinador…»
    (re.compile(rf"([.;])\s+{_LISTA}\s*:\s*(\w)"),   # «…correo.  DT-06: con…»
     lambda m: f"{m.group(1)} {m.group(2).upper() if m.group(1) == '.' else m.group(2)}"),
    (re.compile(rf"\s*\b{_LISTA}\b"), ""),            # los que quedan sueltos
    (re.compile(r"#\d+"), ""),
    (re.compile(r"\(\s*[,;]\s*"), "("),
    (re.compile(r"\s*[,;]\s*\)"), ")"),
    (re.compile(r"\(\s*\)"), ""),
    (re.compile(r"[ \t]+([,.;:)])"), r"\1"),
    (re.compile(r"[ \t]{2,}"), " "),
]


def limpiar(texto: str) -> str:
    """Quita las citas internas (requisitos, decisiones, issues) de una descripción."""
    for patron, reemplazo in _PATRONES:
        texto = patron.sub(reemplazo, texto)
    texto = texto.strip()
    return texto[:1].upper() + texto[1:]


def _recorrer(nodo: Any) -> None:
    if isinstance(nodo, dict):
        for clave in ("description", "summary"):
            if isinstance(nodo.get(clave), str):
                nodo[clave] = limpiar(nodo[clave])
        for valor in nodo.values():
            _recorrer(valor)
    elif isinstance(nodo, list):
        for valor in nodo:
            _recorrer(valor)


def documentar_como_producto(app: FastAPI) -> None:
    """Reemplaza app.openapi por una versión con la descripción del producto y sin citas
    internas. Se calcula una vez y se guarda, como hace FastAPI."""
    original = app.openapi

    def openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema
        esquema = original()
        _recorrer(esquema.get("paths", {}))
        _recorrer(esquema.get("components", {}))
        esquema["info"]["description"] = DESCRIPCION
        app.openapi_schema = esquema
        return esquema

    app.openapi = openapi  # type: ignore[method-assign]
